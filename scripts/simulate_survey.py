#!/usr/bin/env python3
"""
Agent-Separated Survey Simulation Engine

Runs survey simulations with each persona as an independent API call,
eliminating anchoring bias, consensus bias, and style contamination
that occur when all personas share a single LLM context.

Usage:
    python scripts/simulate_survey.py --config configs/rtd-soda-concept-test.json
    python scripts/simulate_survey.py --config configs/rtd-soda-concept-test.json --dry-run
    python scripts/simulate_survey.py --config configs/rtd-soda-concept-test.json --analyze
    python scripts/simulate_survey.py --config configs/rtd-soda-concept-test.json --backend claude-cli --model claude-haiku-4-5-20251001 --concurrency 5
    python scripts/simulate_survey.py --config demo/running-shoes/config.codex.json --backend codex-cli
"""

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from llm_backends import (
    BACKEND_CHOICES,
    REPORT_BACKEND_CHOICES,
    build_json_only_schema,
    describe_backend,
    format_model_label,
    preview_command,
    resolve_backend,
    resolve_model,
    resolve_report_backend,
    run_json_completion_async,
)

# ─── Paths ────────────────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
REFERENCES_DIR = SKILL_DIR / "references"

# Survey type → template file mapping
SURVEY_TYPE_MAP = {
    "concept-test": "concept_test.md",
    "brand-map": "brand_perception.md",
    "price-test": "price_sensitivity.md",
    "usage-habits": "usage_habits.md",
    "survey": "custom_survey.md",
    "ask": "ask.md",
}

# Default config values
DEFAULTS = {
    "backend": "auto",
    "report_backend": "same",
    "max_concurrency": 5,
}

MIN_SUCCESS_RATIO = 0.5  # Abort analysis if fewer than 50% of personas succeed

CONCEPT_OPTION_PATTERN = re.compile(
    r"(?m)^\s*(?:[-*]\s*)?(?:\*\*)?(?P<label>[A-Z])\s*:"
)


# ─── Config Loading ───────────────────────────────────────────────────────────


def load_config(path: Path) -> dict:
    """Load and validate survey config JSON."""
    with open(path) as f:
        config = json.load(f)

    required = ["survey_type", "panel_dir", "variables"]
    missing = [k for k in required if k not in config]
    if missing:
        raise ValueError(
            f"Config missing required fields: {missing}. "
            f"See demo/running-shoes/concept-test/config.json for an example."
        )

    if config["survey_type"] not in SURVEY_TYPE_MAP:
        raise ValueError(
            f"Unknown survey_type: {config['survey_type']}. "
            f"Valid: {list(SURVEY_TYPE_MAP.keys())}"
        )

    # Resolve panel_dir relative to CWD (user's project directory)
    panel_dir = Path(config["panel_dir"])
    if not panel_dir.is_absolute():
        panel_dir = Path.cwd() / panel_dir
    if not panel_dir.is_dir():
        raise FileNotFoundError(
            f"Panel directory not found: {panel_dir}\n"
            f"Run '/persona generate' first, or check 'panel_dir' in your config."
        )
    config["_panel_dir"] = panel_dir

    # Resolve output_dir relative to CWD (user's project directory)
    if "output_dir" in config:
        output_dir = Path(config["output_dir"])
        if not output_dir.is_absolute():
            output_dir = Path.cwd() / output_dir
    else:
        ts = datetime.now().strftime("%Y-%m-%d/%H%M%S")
        topic_slug = re.sub(
            r"[^a-z0-9]+", "-",
            (config.get("topic", "") or "").lower(),
        ).strip("-")[:30]
        dir_name = config["survey_type"]
        if topic_slug:
            dir_name = f"{dir_name}-{topic_slug}"
        output_dir = Path.cwd() / "outputs" / ts / dir_name
    config["_output_dir"] = output_dir

    # Apply defaults
    for k, v in DEFAULTS.items():
        config.setdefault(k, v)

    return config


def resolve_runtime_settings(config: dict) -> dict:
    """Resolve runtime backend/model settings after config + CLI overrides."""
    resolved_backend = resolve_backend(config.get("backend"))
    resolved_model = resolve_model(config.get("model"), resolved_backend)

    resolved_report_backend = resolve_report_backend(
        config.get("report_backend"),
        resolved_backend,
    )
    if resolved_report_backend == "python":
        resolved_report_model = None
    elif config.get("report_model"):
        resolved_report_model = resolve_model(
            config.get("report_model"),
            resolved_report_backend,
        )
    elif resolved_report_backend == resolved_backend:
        resolved_report_model = resolved_model
    else:
        resolved_report_model = resolve_model(None, resolved_report_backend)

    config["_resolved_backend"] = resolved_backend
    config["_resolved_model"] = resolved_model
    config["_resolved_report_backend"] = resolved_report_backend
    config["_resolved_report_model"] = resolved_report_model
    return config


def extract_allowed_concept_options(variables: dict | None) -> set[str]:
    """Extract concept labels like A/B/C from markdown-style concept blocks."""
    concepts = ""
    if variables:
        concepts = str(variables.get("concepts", "") or "")
    return {match.group("label") for match in CONCEPT_OPTION_PATTERN.finditer(concepts)}


# ─── Persona Loading ──────────────────────────────────────────────────────────


def load_personas(panel_dir: Path) -> list[dict]:
    """Load persona files via manifest.json."""
    manifest_path = panel_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"manifest.json not found in {panel_dir}. "
            f"Run '/persona generate' first, or check your panel_dir path."
        )

    with open(manifest_path) as f:
        manifest = json.load(f)

    personas = []
    for filename in manifest["persona_files"]:
        persona_path = panel_dir / filename
        if not persona_path.exists():
            print(f"WARNING: Persona file not found: {persona_path}", file=sys.stderr)
            continue
        with open(persona_path) as f:
            personas.append(json.load(f))

    if not personas:
        raise ValueError(
            f"No persona files loaded from {panel_dir}. "
            f"Check that manifest.json lists valid filenames."
        )

    return personas


# ─── Profile Extraction ──────────────────────────────────────────────────────


def first_sentence(text: str) -> str:
    """Extract the first sentence from text."""
    if not text:
        return ""
    # Split on period followed by space or end of string
    match = re.match(r"^(.*?\.)\s", text)
    if match:
        return match.group(1)
    # If no period+space found, return up to first period or full text
    dot_pos = text.find(".")
    if dot_pos > 0:
        return text[: dot_pos + 1]
    return text


def _score_relevance(item: str, topic_words: set[str]) -> int:
    """Score item relevance to topic by word overlap. 0-3."""
    item_words = set(item.lower().split())
    overlap = len(item_words & topic_words)
    if overlap >= 2:
        return 3
    elif overlap == 1:
        return 2
    return 1  # personality-revealing default


def _select_relevant(items: list[str], topic: str, n: int = 5) -> list[str]:
    """Select up to n items prioritized by topic relevance."""
    if not topic:
        return items[:n]
    topic_words = set(topic.lower().split())
    scored = [(item, _score_relevance(item, topic_words)) for item in items]
    scored.sort(key=lambda x: -x[1])
    return [item for item, _ in scored[:n]]


def extract_simulation_profile(full_persona: dict, topic: str = "") -> dict:
    """Extract compact simulation profile from full persona JSON.

    Keeps response-driving fields, drops verbose/irrelevant fields.
    Implements the rules from simulation-profile-extractor.md.
    Interests/likes/dislikes are prioritized by topic relevance.
    """
    p = full_persona["persona"]

    profile = {
        "name": p["name"],
        "age": p["age"],
        "gender": p["gender"],
        "occupation": p["occupation"]["title"],
        "organization": p["occupation"].get("organization", ""),
        "residence": p.get("residence", ""),
        "education": first_sentence(p.get("education", "")),
        "style": p.get("style", ""),  # Full text — never truncate
        "personality": {
            "big_five": p["personality"]["big_five"],
            "traits": p["personality"].get("traits", [])[:5],
        },
        "interests": _select_relevant(
            p.get("preferences", {}).get("interests", []), topic, 5
        ),
        "likes": _select_relevant(
            p.get("preferences", {}).get("likes", []), topic, 5
        ),
        "dislikes": _select_relevant(
            p.get("preferences", {}).get("dislikes", []), topic, 5
        ),
        "beliefs": p.get("beliefs", [])[:3],
        "segment": full_persona.get("segment", ""),
        "segment_id": full_persona.get("segment_id", None),
    }

    return profile


# ─── Prompt Construction ──────────────────────────────────────────────────────


def load_simulation_prompt() -> str:
    """Load the simulation-prompt.md template.

    The prompt content is between the first ``` and the final ``` in the file.
    We use a greedy match to capture nested code blocks too.
    """
    path = REFERENCES_DIR / "simulation-prompt.md"
    with open(path) as f:
        content = f.read()
    # Greedy match: capture everything between first ``` and last ```
    match = re.search(r"```\n(.*)\n```", content, re.DOTALL)
    if match:
        return match.group(1)
    raise ValueError("Could not extract prompt template from simulation-prompt.md")


def load_survey_template(survey_type: str) -> str:
    """Load the survey question template."""
    filename = SURVEY_TYPE_MAP[survey_type]
    path = TEMPLATES_DIR / filename
    with open(path) as f:
        return f.read()


def check_unresolved_placeholders(template: str, variables: dict) -> list[str]:
    """Return any {{key}} placeholders in template not covered by variables."""
    placeholders = set(re.findall(r"\{\{(\w+)\}\}", template))
    return sorted(placeholders - set(variables.keys()))


def substitute_variables(template: str, variables: dict) -> str:
    """Replace {{key}} placeholders in template with variable values."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def build_single_persona_prompt(
    simulation_prompt: str,
    survey_template: str,
    persona_profile: dict,
    variables: dict,
    topic: str = "",
) -> str:
    """Build a complete prompt for a single persona's survey response.

    Transforms the multi-persona simulation-prompt.md into a
    single-persona version at runtime.
    """
    # Start with the simulation prompt
    prompt = simulation_prompt

    # Transform multi-persona instructions to single-persona
    prompt = prompt.replace(
        "You will role-play as multiple\npersonas, answering survey questions AS each person would.",
        "You will role-play as one specific consumer. Answer the survey questions "
        "AS this person would — grounded in their personality, background, and life circumstances.",
    )

    # Replace persona definitions section
    persona_json = json.dumps(persona_profile, indent=2, ensure_ascii=False)
    prompt = prompt.replace(
        "## Persona Definitions\n\n{PERSONAS_JSON}",
        f"## Your Persona\n\n{persona_json}",
    )

    # Replace output format section
    prompt = prompt.replace(
        "Return a JSON array. Each element is one persona's complete response:",
        "Return a single JSON object with your complete response. "
        "Do not repeat persona metadata at the top level; return only the survey "
        "answers inside `responses`:",
    )

    # Replace the JSON example block (array → single object)
    # The example may appear with or without code fences
    new_example = (
        "```json\n"
        "{\n"
        '  "responses": {\n'
        '    "question_1_key": "answer",\n'
        '    "question_2_key": "answer"\n'
        "  }\n"
        "}\n"
        "```"
    )
    # Remove the old JSON array example block (between ```json and ```)
    prompt = re.sub(
        r"```json\s*\n\[\s*\{.*?\}\s*,?\s*\.\.\.\s*\]\s*\n```",
        new_example,
        prompt,
        flags=re.DOTALL,
    )

    # Substitute survey questions
    survey_content = substitute_variables(survey_template, variables)
    prompt = prompt.replace("{SURVEY_QUESTIONS}", survey_content)

    # Substitute concepts/stimuli
    concepts = variables.get("concepts", variables.get("product_description", "N/A"))
    prompt = prompt.replace("{CONCEPTS}", str(concepts))

    return prompt


# ─── Response Validation ──────────────────────────────────────────────────────


REQUIRED_RESPONSE_KEYS = {
    "concept-test": ["preferred_option", "reasoning"],
    "brand-map": [
        "unaided_awareness",
        "aided_familiarity",
        "brand_buckets",
        "consideration_set",
        "brand_associations",
    ],
    "price-test": [
        "max_wtp",
        "intent_by_price",
        "value_perception",
        "competitive_reference",
        "price_quality_preference",
        "reasoning",
    ],
    "usage-habits": [
        "usage_frequency",
        "current_product",
        "purchase_channel",
        "factor_ranking",
        "pain_points",
        "info_sources",
    ],
    "survey": [],
    "ask": ["short_answer", "reasoning"],
}

BRAND_FAMILIARITY_VALUES = {"know_well", "heard_of", "unknown"}
BRAND_BUCKET_KEYS = ("like", "dislike", "neutral")
PRICE_QUALITY_PREFERENCE_VALUES = {"cheaper", "expensive", "depends"}
USAGE_FREQUENCY_VALUES = {"daily", "weekly", "monthly", "rarely", "never"}


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_string_list(value: object, max_items: int | None = None) -> bool:
    if not isinstance(value, list):
        return False
    if max_items is not None and len(value) > max_items:
        return False
    return all(_is_non_empty_string(item) for item in value)


def build_response_schema(
    survey_type: str,
    allowed_options: set[str] | None = None,
) -> dict:
    """Build a minimal JSON schema for Codex structured outputs."""
    schema = build_json_only_schema(
        REQUIRED_RESPONSE_KEYS.get(survey_type, []),
    )
    responses_schema = schema["properties"]["responses"]
    response_properties = responses_schema.setdefault("properties", {})

    if survey_type == "concept-test":
        if allowed_options:
            response_properties["preferred_option"] = {
                "type": "string",
                "enum": sorted(allowed_options),
            }
        response_properties.setdefault(
            "reasoning",
            {"type": "string", "minLength": 1},
        )
    elif survey_type == "brand-map":
        response_properties.update(
            {
                "unaided_awareness": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 3,
                },
                "aided_familiarity": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "string",
                        "enum": sorted(BRAND_FAMILIARITY_VALUES),
                    },
                },
                "brand_buckets": {
                    "type": "object",
                    "properties": {
                        bucket: {
                            "type": "array",
                            "items": {"type": "string"},
                        }
                        for bucket in BRAND_BUCKET_KEYS
                    },
                    "required": list(BRAND_BUCKET_KEYS),
                    "additionalProperties": False,
                },
                "consideration_set": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 5,
                },
                "brand_associations": {
                    "type": "object",
                    "additionalProperties": {"type": "string", "minLength": 1},
                },
            }
        )
    elif survey_type == "price-test":
        response_properties.update(
            {
                "max_wtp": {"type": "number", "exclusiveMinimum": 0},
                "intent_by_price": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "number",
                        "minimum": 1,
                        "maximum": 5,
                    },
                },
                "value_perception": {"type": "string", "minLength": 1},
                "competitive_reference": {
                    "anyOf": [
                        {"type": "number", "exclusiveMinimum": 0},
                        {"type": "string", "enum": ["unsure"]},
                    ]
                },
                "price_quality_preference": {
                    "type": "string",
                    "enum": sorted(PRICE_QUALITY_PREFERENCE_VALUES),
                },
                "reasoning": {"type": "string", "minLength": 1},
            }
        )
    elif survey_type == "usage-habits":
        response_properties.update(
            {
                "usage_frequency": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "string",
                        "enum": sorted(USAGE_FREQUENCY_VALUES),
                    },
                },
                "current_product": {"type": "string", "minLength": 1},
                "purchase_channel": {"type": "string", "minLength": 1},
                "factor_ranking": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "number",
                        "minimum": 1,
                    },
                },
                "pain_points": {"type": "string", "minLength": 1},
                "info_sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 3,
                },
            }
        )
    elif survey_type == "ask":
        response_properties.update(
            {
                "short_answer": {"type": "string", "minLength": 1},
                "reasoning": {"type": "string", "minLength": 1},
                "themes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 4,
                },
                "emotion": {"type": "string"},
            }
        )

    return schema


async def run_backend_preflight(config: dict) -> dict:
    """Run one minimal backend call before persona fan-out."""
    start_time = time.monotonic()
    result = {
        "success": False,
        "backend": config["_resolved_backend"],
        "resolved_model": config.get("_resolved_model"),
        "check": "minimal-json-completion",
        "usage_supported": config["_resolved_backend"] == "claude-cli",
        "input_tokens": 0,
        "output_tokens": 0,
        "latency_ms": 0,
        "error": None,
    }

    try:
        completion = await run_json_completion_async(
            backend=config["_resolved_backend"],
            system_prompt=(
                "You are a connectivity preflight check. "
                "Return only the JSON object requested by the user."
            ),
            user_message=(
                "Return exactly this JSON object: "
                '{"status":"ok","check":"backend_preflight"}'
            ),
            model=config.get("_resolved_model"),
            json_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "check": {"type": "string"},
                },
                "required": ["status", "check"],
                "additionalProperties": False,
            },
            cwd=SKILL_DIR,
            timeout_s=60,
        )
        payload = completion["data"]
        if payload.get("status") != "ok":
            raise ValueError(f"Unexpected preflight payload: {payload}")

        result["success"] = True
        result["usage_supported"] = completion["usage_supported"]
        result["input_tokens"] = completion["input_tokens"]
        result["output_tokens"] = completion["output_tokens"]
    except Exception as error:
        result["error"] = str(error)
    finally:
        result["latency_ms"] = int((time.monotonic() - start_time) * 1000)

    return result


def validate_response(
    response: dict,
    survey_type: str,
    allowed_options: set[str] | None = None,
) -> list[str]:
    """Validate a parsed response object. Returns list of issues (empty = valid)."""
    issues = []

    if not isinstance(response, dict):
        return ["Response must be a JSON object"]

    # Canonical contract: response data must live inside `responses`
    if "responses" not in response or not isinstance(response.get("responses"), dict):
        issues.append("Missing or invalid 'responses' field")

    # Survey-type-specific validation
    responses = response.get("responses", {})
    for key in REQUIRED_RESPONSE_KEYS.get(survey_type, []):
        if key not in responses:
            issues.append(f"Missing '{key}' in responses")

    if survey_type == "concept-test":
        preferred_option = responses.get("preferred_option")
        if "preferred_option" in responses and allowed_options:
            if str(preferred_option).strip() not in allowed_options:
                issues.append("Invalid 'preferred_option' in responses")

        reasoning = responses.get("reasoning")
        if "reasoning" in responses:
            if not isinstance(reasoning, str) or not reasoning.strip():
                issues.append("Invalid 'reasoning' in responses")
    elif survey_type == "brand-map":
        awareness = responses.get("unaided_awareness")
        if "unaided_awareness" in responses and not _is_string_list(awareness, max_items=3):
            issues.append("Invalid 'unaided_awareness' in responses")

        familiarity = responses.get("aided_familiarity")
        if "aided_familiarity" in responses:
            if not isinstance(familiarity, dict) or not familiarity:
                issues.append("Invalid 'aided_familiarity' in responses")
            elif any(str(value).strip() not in BRAND_FAMILIARITY_VALUES for value in familiarity.values()):
                issues.append("Invalid 'aided_familiarity' in responses")

        buckets = responses.get("brand_buckets")
        if "brand_buckets" in responses:
            if not isinstance(buckets, dict):
                issues.append("Invalid 'brand_buckets' in responses")
            else:
                missing_buckets = [bucket for bucket in BRAND_BUCKET_KEYS if bucket not in buckets]
                if missing_buckets:
                    issues.append("Invalid 'brand_buckets' in responses")
                elif any(not _is_string_list(buckets.get(bucket, [])) for bucket in BRAND_BUCKET_KEYS):
                    issues.append("Invalid 'brand_buckets' in responses")

        consideration = responses.get("consideration_set")
        if "consideration_set" in responses and not _is_string_list(consideration, max_items=5):
            issues.append("Invalid 'consideration_set' in responses")

        associations = responses.get("brand_associations")
        if "brand_associations" in responses:
            if not isinstance(associations, dict):
                issues.append("Invalid 'brand_associations' in responses")
            elif any(not _is_non_empty_string(value) for value in associations.values()):
                issues.append("Invalid 'brand_associations' in responses")
    elif survey_type == "price-test":
        max_wtp = responses.get("max_wtp")
        if "max_wtp" in responses and (not _is_number(max_wtp) or float(max_wtp) <= 0):
            issues.append("Invalid 'max_wtp' in responses")

        intent_by_price = responses.get("intent_by_price")
        if "intent_by_price" in responses:
            if not isinstance(intent_by_price, dict) or not intent_by_price:
                issues.append("Invalid 'intent_by_price' in responses")
            else:
                invalid_intent = any(
                    (not _is_number(intent)) or not (1 <= float(intent) <= 5)
                    for intent in intent_by_price.values()
                )
                if invalid_intent:
                    issues.append("Invalid 'intent_by_price' in responses")

        value_perception = responses.get("value_perception")
        if "value_perception" in responses and not _is_non_empty_string(value_perception):
            issues.append("Invalid 'value_perception' in responses")

        competitive_reference = responses.get("competitive_reference")
        if "competitive_reference" in responses:
            valid_reference = (
                (_is_number(competitive_reference) and float(competitive_reference) > 0)
                or str(competitive_reference).strip() == "unsure"
            )
            if not valid_reference:
                issues.append("Invalid 'competitive_reference' in responses")

        preference = responses.get("price_quality_preference")
        if "price_quality_preference" in responses:
            if str(preference).strip() not in PRICE_QUALITY_PREFERENCE_VALUES:
                issues.append("Invalid 'price_quality_preference' in responses")

        reasoning = responses.get("reasoning")
        if "reasoning" in responses and not _is_non_empty_string(reasoning):
            issues.append("Invalid 'reasoning' in responses")
    elif survey_type == "usage-habits":
        usage_frequency = responses.get("usage_frequency")
        if "usage_frequency" in responses:
            if not isinstance(usage_frequency, dict) or not usage_frequency:
                issues.append("Invalid 'usage_frequency' in responses")
            else:
                invalid_frequency = any(
                    str(value).strip().lower() not in USAGE_FREQUENCY_VALUES
                    for value in usage_frequency.values()
                )
                if invalid_frequency:
                    issues.append("Invalid 'usage_frequency' in responses")

        for key in ["current_product", "purchase_channel", "pain_points"]:
            value = responses.get(key)
            if key in responses and not _is_non_empty_string(value):
                issues.append(f"Invalid '{key}' in responses")

        factor_ranking = responses.get("factor_ranking")
        if "factor_ranking" in responses:
            if not isinstance(factor_ranking, dict) or not factor_ranking:
                issues.append("Invalid 'factor_ranking' in responses")
            else:
                numeric_ranks = []
                invalid_rank = False
                for rank in factor_ranking.values():
                    if not _is_number(rank) or float(rank) < 1:
                        invalid_rank = True
                        break
                    numeric_ranks.append(float(rank))
                if invalid_rank or len(set(numeric_ranks)) != len(numeric_ranks):
                    issues.append("Invalid 'factor_ranking' in responses")

        info_sources = responses.get("info_sources")
        if "info_sources" in responses:
            if not _is_string_list(info_sources, max_items=3) or not info_sources:
                issues.append("Invalid 'info_sources' in responses")
    elif survey_type == "ask":
        short_answer = responses.get("short_answer")
        if "short_answer" in responses and not _is_non_empty_string(short_answer):
            issues.append("Invalid 'short_answer' in responses")

        reasoning = responses.get("reasoning")
        if "reasoning" in responses and not _is_non_empty_string(reasoning):
            issues.append("Invalid 'reasoning' in responses")

        themes = responses.get("themes")
        if "themes" in responses and not isinstance(themes, list):
            issues.append("Invalid 'themes' in responses")

        emotion = responses.get("emotion")
        if "emotion" in responses and emotion is not None and not _is_non_empty_string(emotion):
            issues.append("Invalid 'emotion' in responses")

    return issues


def load_adherence_prompt() -> str:
    """Load the adherence-check-prompt.md template."""
    path = REFERENCES_DIR / "adherence-check-prompt.md"
    with open(path) as f:
        content = f.read()
    match = re.search(r"```\n(.*)\n```", content, re.DOTALL)
    if match:
        return match.group(1)
    raise ValueError("Could not extract prompt from adherence-check-prompt.md")


async def check_persona_adherence(
    persona_profile: dict,
    response: dict,
    adherence_prompt_template: str,
    config: dict,
    semaphore: asyncio.Semaphore,
) -> dict:
    """Check if a survey response adheres to the persona profile using LLM evaluation.

    Returns dict with pass/fail, score, feedback, and token tracking.
    """
    result = {"pass": True, "score": None, "feedback": "", "error": None,
              "input_tokens": 0, "output_tokens": 0}

    # Build the checking prompt
    system_prompt = adherence_prompt_template.replace(
        "{PERSONA_JSON}", json.dumps(persona_profile, indent=2, ensure_ascii=False)
    ).replace(
        "{RESPONSE_JSON}", json.dumps(response, indent=2, ensure_ascii=False)
    )

    user_msg = "Evaluate this survey response against the persona profile. Return only the JSON scoring object."
    scoring_schema = {
        "type": "object",
        "properties": {
            "overall_score": {"type": "number"},
            "issues": {"type": "array", "items": {"type": "string"}},
            "feedback_for_regeneration": {"type": "string"},
        },
        "required": ["overall_score"],
        "additionalProperties": True,
    }

    async with semaphore:
        try:
            completion = await run_json_completion_async(
                backend=config["_resolved_backend"],
                system_prompt=system_prompt,
                user_message=user_msg,
                model=config.get("_resolved_model"),
                json_schema=scoring_schema,
                cwd=SKILL_DIR,
            )
            result["input_tokens"] = completion["input_tokens"]
            result["output_tokens"] = completion["output_tokens"]
            scoring = completion["data"]
            score = scoring.get("overall_score", 7)
            result["score"] = int(score)
            result["pass"] = result["score"] >= 7
            if not result["pass"]:
                result["feedback"] = scoring.get("feedback_for_regeneration", "")
                issues = scoring.get("issues", [])
                if issues and not result["feedback"]:
                    result["feedback"] = "; ".join(issues)

        except Exception as e:
            result["error"] = str(e)

    return result


async def call_backend_for_persona(
    system_prompt: str,
    user_message: str,
    persona_name: str,
    config: dict,
    semaphore: asyncio.Semaphore,
    max_retries: int = 3,
    persona_profile: dict | None = None,
    adherence_prompt: str | None = None,
) -> dict:
    """Call the resolved backend for one persona with retries and adherence checks."""

    result = {
        "persona_name": persona_name,
        "success": False,
        "response": None,
        "validation_issues": [],
        "input_tokens": 0,
        "output_tokens": 0,
        "latency_ms": 0,
        "attempts": 0,
        "error": None,
        "first_adherence_score": None,
        "first_adherence_passed": None,
        "adherence_score": None,
        "adherence_passed": None,
        "adherence_retried": False,
        "usage_supported": config["_resolved_backend"] == "claude-cli",
    }

    start_time = time.monotonic()
    allowed_options = config.get("_allowed_concept_options")
    response_schema = build_response_schema(
        config["survey_type"],
        allowed_options=allowed_options,
    )

    async with semaphore:
        for attempt in range(1, max_retries + 1):
            result["attempts"] = attempt

            try:
                completion = await run_json_completion_async(
                    backend=config["_resolved_backend"],
                    system_prompt=system_prompt,
                    user_message=user_message,
                    model=config.get("_resolved_model"),
                    json_schema=response_schema,
                    cwd=SKILL_DIR,
                )
                result["input_tokens"] = completion["input_tokens"]
                result["output_tokens"] = completion["output_tokens"]
                result["usage_supported"] = completion["usage_supported"]
                parsed = completion["data"]
                issues = validate_response(
                    parsed,
                    config["survey_type"],
                    allowed_options=allowed_options,
                )

                if issues:
                    result["validation_issues"] = issues
                    if attempt < max_retries:
                        print(
                            f"  [{persona_name}] Attempt {attempt}: validation issues: {issues}. Retrying...",
                            file=sys.stderr,
                        )
                        await asyncio.sleep(1 * attempt)
                        continue
                    else:
                        print(
                            f"  [{persona_name}] Validation issues after {max_retries} attempts: {issues}",
                            file=sys.stderr,
                        )
                        result["error"] = "Validation failed: " + "; ".join(issues)
                        return result

                result["validation_issues"] = []
                result["response"] = parsed
                result["success"] = True
                break  # proceed to adherence check

            except Exception as e:
                err_text = str(e)
                if attempt < max_retries:
                    wait = 2 * attempt
                    print(
                        f"  [{persona_name}] Backend error (attempt {attempt}): {err_text[:200]}. Retrying in {wait}s...",
                        file=sys.stderr,
                    )
                    await asyncio.sleep(wait)
                    continue
                result["error"] = err_text[:500]
                return result

    # Phase 2: Persona adherence check (if enabled and generation succeeded)
    if (
        result["success"]
        and persona_profile is not None
        and adherence_prompt is not None
    ):
        adherence = await check_persona_adherence(
            persona_profile, result["response"],
            adherence_prompt, config, semaphore,
        )
        # Accumulate tokens from adherence check
        result["input_tokens"] += adherence.get("input_tokens", 0)
        result["output_tokens"] += adherence.get("output_tokens", 0)

        if adherence.get("error"):
            print(
                f"  [{persona_name}] Adherence check error: {adherence['error'][:100]}. Skipping.",
                file=sys.stderr,
            )
        elif adherence["score"] is not None:
            result["first_adherence_score"] = adherence["score"]
            result["first_adherence_passed"] = adherence["pass"]
            result["adherence_score"] = adherence["score"]
            result["adherence_passed"] = adherence["pass"]

            if not adherence["pass"]:
                print(
                    f"  [{persona_name}] Adherence score {adherence['score']}/10. Regenerating...",
                    file=sys.stderr,
                )
                result["adherence_retried"] = True

                # Regenerate with feedback
                regen_message = (
                    f"Your previous response did not adequately reflect this persona's profile. "
                    f"Specific issues:\n{adherence['feedback']}\n\n"
                    f"Please regenerate the survey response, paying close attention to the "
                    f"persona's style, Big Five personality traits, and background. "
                    f"Return only valid JSON — no markdown, no explanation."
                )
                try:
                    regen_completion = await run_json_completion_async(
                        backend=config["_resolved_backend"],
                        system_prompt=system_prompt,
                        user_message=regen_message,
                        model=config.get("_resolved_model"),
                        json_schema=response_schema,
                        cwd=SKILL_DIR,
                    )
                    result["input_tokens"] += regen_completion["input_tokens"]
                    result["output_tokens"] += regen_completion["output_tokens"]
                    regen_parsed = regen_completion["data"]
                    regen_issues = validate_response(
                        regen_parsed,
                        config["survey_type"],
                        allowed_options=allowed_options,
                    )
                    if not regen_issues:
                        result["response"] = regen_parsed
                        result["validation_issues"] = []
                        # Re-score the regenerated response
                        recheck = await check_persona_adherence(
                            persona_profile, regen_parsed,
                            adherence_prompt, config, semaphore,
                        )
                        result["input_tokens"] += recheck.get("input_tokens", 0)
                        result["output_tokens"] += recheck.get("output_tokens", 0)
                        if recheck.get("score") is not None:
                            result["adherence_score"] = recheck["score"]
                            result["adherence_passed"] = recheck["pass"]
                    else:
                        print(
                            f"  [{persona_name}] Regeneration validation issues: {regen_issues}. Keeping original.",
                            file=sys.stderr,
                        )
                except Exception as e:
                    print(
                        f"  [{persona_name}] Regeneration failed: {e}. Keeping original.",
                        file=sys.stderr,
                    )

    # Update total latency
    result["latency_ms"] = int((time.monotonic() - start_time) * 1000)

    return result


# ─── Result Assembly ──────────────────────────────────────────────────────────


def assemble_results(
    api_results: list[dict], personas: list[dict]
) -> list[dict]:
    """Assemble individual API results into results.json format.

    Produces output compatible with analyze_results.py.
    """
    persona_lookup = {
        p["persona"]["name"]: {
            "name": p["persona"]["name"],
            "segment": p.get("segment", ""),
            "age": p["persona"].get("age"),
            "gender": p["persona"].get("gender", ""),
            "occupation": p["persona"].get("occupation", {}).get("title", ""),
        }
        for p in personas
    }

    results = []
    for api_result in api_results:
        if not api_result["success"] or api_result["response"] is None:
            print(
                f"WARNING: Skipping {api_result['persona_name']} — "
                f"error: {api_result.get('error', 'unknown')}",
                file=sys.stderr,
            )
            continue

        resp = api_result["response"]
        persona_meta = persona_lookup.get(
            api_result["persona_name"],
            {
                "name": api_result["persona_name"],
                "segment": "",
                "age": None,
                "gender": "",
                "occupation": "",
            },
        )
        entry = {
            "name": persona_meta["name"],
            "segment": persona_meta["segment"],
            "age": persona_meta["age"],
            "gender": persona_meta["gender"],
            "occupation": persona_meta["occupation"],
            "responses": resp.get("responses", {}),
        }

        results.append(entry)

    return results


def build_run_metadata(
    config: dict,
    api_results: list[dict],
    total_elapsed_ms: int,
    preflight_result: dict | None = None,
    failure_stage: str | None = None,
) -> dict:
    """Build run_metadata.json content."""
    successful = sum(1 for r in api_results if r["success"])
    usage_supported = any(r.get("usage_supported", False) for r in api_results)
    if preflight_result and preflight_result.get("usage_supported", False):
        usage_supported = True

    if usage_supported:
        total_input = sum(r["input_tokens"] for r in api_results)
        total_output = sum(r["output_tokens"] for r in api_results)
        if preflight_result and preflight_result.get("usage_supported"):
            total_input += preflight_result.get("input_tokens", 0)
            total_output += preflight_result.get("output_tokens", 0)
        total_tokens = total_input + total_output
    else:
        total_input = None
        total_output = None
        total_tokens = None

    def first_adherence_score(result: dict):
        if result.get("first_adherence_score") is not None:
            return result.get("first_adherence_score")
        if result.get("adherence_score") is not None and not result.get("adherence_retried", False):
            return result.get("adherence_score")
        return None

    def first_adherence_passed(result: dict):
        if result.get("first_adherence_passed") is not None:
            return result.get("first_adherence_passed")
        if result.get("adherence_passed") is not None and not result.get("adherence_retried", False):
            return result.get("adherence_passed")
        return None

    def serialize_config_path(config_path: str | None) -> str:
        if not config_path:
            return ""
        path = Path(config_path)
        if path.is_absolute():
            try:
                return path.relative_to(Path.cwd()).as_posix()
            except ValueError:
                return str(path)
        return path.as_posix()

    checked = [
        r for r in api_results
        if first_adherence_score(r) is not None or r.get("adherence_score") is not None
    ]
    adherence_stats = {
        "enabled": len(checked) > 0,
        "total_checked": len(checked),
        "passed_first_try": sum(1 for r in checked if first_adherence_passed(r) is True),
        "passed_after_retry": sum(
            1
            for r in checked
            if r.get("adherence_retried", False) and r.get("adherence_passed") is True
        ),
        "retried": sum(1 for r in api_results if r.get("adherence_retried", False)),
        "mean_score": (
            round(sum(r["adherence_score"] for r in checked) / len(checked), 1)
            if checked else None
        ),
    }

    per_persona = []
    for r in api_results:
        persona_first_adherence_score = first_adherence_score(r)
        persona_first_adherence_passed = first_adherence_passed(r)
        per_persona.append(
            {
                "name": r["persona_name"],
                "success": r["success"],
                "usage_supported": r.get("usage_supported", False),
                "input_tokens": r["input_tokens"] if r.get("usage_supported") else None,
                "output_tokens": r["output_tokens"] if r.get("usage_supported") else None,
                "latency_ms": r["latency_ms"],
                "attempts": r["attempts"],
                "first_adherence_score": persona_first_adherence_score,
                "first_adherence_passed": persona_first_adherence_passed,
                "adherence_score": r.get("adherence_score"),
                "adherence_passed": r.get("adherence_passed"),
                "adherence_retried": r.get("adherence_retried", False),
                "validation_issues": r.get("validation_issues", []),
                "error": r.get("error"),
            }
        )

    return {
        "schema_version": 2,
        "isolation_mode": "agent-separated",
        "backend": config["_resolved_backend"],
        "resolved_model": config.get("_resolved_model"),
        "failure_stage": failure_stage,
        "usage_supported": usage_supported,
        "temperature": f"N/A ({config['_resolved_backend']})",
        "total_personas": len(api_results),
        "successful": successful,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_tokens,
        "total_elapsed_ms": total_elapsed_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topic": config.get("topic"),
        "user_question": config.get("variables", {}).get("user_question"),
        "config_file": serialize_config_path(config.get("_config_path")),
        "preflight": {
            "success": preflight_result.get("success"),
            "backend": preflight_result.get("backend"),
            "resolved_model": preflight_result.get("resolved_model"),
            "check": preflight_result.get("check"),
            "usage_supported": preflight_result.get("usage_supported"),
            "input_tokens": (
                preflight_result.get("input_tokens")
                if preflight_result.get("usage_supported")
                else None
            ),
            "output_tokens": (
                preflight_result.get("output_tokens")
                if preflight_result.get("usage_supported")
                else None
            ),
            "latency_ms": preflight_result.get("latency_ms"),
            "error": preflight_result.get("error"),
        } if preflight_result else None,
        "adherence_checks": adherence_stats,
        "per_persona": per_persona,
    }


def save_run_artifacts(
    config: dict,
    results: list[dict],
    api_results: list[dict],
    total_elapsed_ms: int,
    preflight_result: dict | None = None,
    failure_stage: str | None = None,
) -> None:
    """Persist results and metadata for both success and failure paths."""
    output_dir = config["_output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / "results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved results: {results_path}")

    metadata = build_run_metadata(
        config,
        api_results,
        total_elapsed_ms,
        preflight_result=preflight_result,
        failure_stage=failure_stage,
    )
    metadata_path = output_dir / "run_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"Saved metadata: {metadata_path}")


# ─── Main Orchestration ──────────────────────────────────────────────────────


async def run_simulation(config: dict, dry_run: bool = False) -> list[dict]:
    """Run the full simulation pipeline."""
    overall_start = time.monotonic()
    print(f"Survey type: {config['survey_type']}")
    print(f"Backend: {config['_resolved_backend']}")
    print(f"Model: {format_model_label(config.get('_resolved_model'))}")
    print(f"Execution: {describe_backend(config['_resolved_backend'])}")
    print(f"Max concurrency: {config['max_concurrency']}")
    print()

    if not dry_run:
        print("Running backend preflight...")
        preflight_result = await run_backend_preflight(config)
        if not preflight_result["success"]:
            total_elapsed_ms = int((time.monotonic() - overall_start) * 1000)
            print(
                "ERROR: Backend preflight failed. Aborting before persona fan-out.",
                file=sys.stderr,
            )
            if preflight_result.get("error"):
                print(preflight_result["error"][:1200], file=sys.stderr)
            save_run_artifacts(
                config,
                results=[],
                api_results=[],
                total_elapsed_ms=total_elapsed_ms,
                preflight_result=preflight_result,
                failure_stage="preflight",
            )
            return []

        latency_ms = preflight_result["latency_ms"]
        print(f"Backend preflight: OK ({latency_ms}ms)")
    else:
        preflight_result = None

    # 1. Load personas
    panel_dir = config["_panel_dir"]
    print(f"Loading personas from: {panel_dir}")
    personas = load_personas(panel_dir)
    print(f"Loaded {len(personas)} personas")

    # 2. Load templates
    simulation_prompt = load_simulation_prompt()
    survey_template = load_survey_template(config["survey_type"])
    topic = config.get("topic", "")

    # 2b. Validate template placeholders
    unresolved = check_unresolved_placeholders(
        survey_template, config.get("variables", {})
    )
    if unresolved:
        raise ValueError(
            f"Survey template has unresolved placeholders: {unresolved}. "
            f"Add these keys to 'variables' in your config JSON. "
            f"See demo/running-shoes/concept-test/config.json for an example."
        )

    # 3. Build per-persona prompts
    print("\nBuilding per-persona prompts...")
    persona_prompts = []
    for persona in personas:
        profile = extract_simulation_profile(persona, topic)
        prompt = build_single_persona_prompt(
            simulation_prompt,
            survey_template,
            profile,
            config["variables"],
            topic,
        )
        persona_prompts.append((persona["persona"]["name"], profile, prompt))

    # 4. Dry run — print first persona's prompt and exit
    if dry_run:
        name, profile, prompt = persona_prompts[0]
        print(f"\n{'='*60}")
        print(f"DRY RUN — Prompt for: {name}")
        print(f"{'='*60}")
        print(f"\n--- BACKEND COMMAND ---\n")
        print(
            preview_command(
                config["_resolved_backend"],
                model=config.get("_resolved_model"),
                structured_output=True,
            )
        )
        print(f"\n--- SYSTEM PROMPT ({len(prompt)} chars) ---\n")
        print(prompt)
        print(f"\n--- USER MESSAGE (stdin) ---\n")
        print(
            "Answer the survey questions as this persona. "
            "Return only valid JSON — no markdown, no explanation."
        )
        print(f"\n{'='*60}")
        print(f"Total personas: {len(persona_prompts)}")
        return []

    # 5. Load adherence check prompt (if available)
    adherence_prompt = None
    if not config.get("_no_adherence_check", False):
        try:
            adherence_prompt = load_adherence_prompt()
            print("Adherence check: enabled")
        except (FileNotFoundError, ValueError):
            print("Adherence check: disabled (prompt not found)")
    else:
        print("Adherence check: disabled (--no-adherence-check)")

    # 6. Run parallel backend calls
    user_message = (
        "Answer the survey questions as this persona. "
        "Return only valid JSON — no markdown, no explanation."
    )
    print(
        f"\nStarting {len(persona_prompts)} parallel {config['_resolved_backend']} calls..."
    )
    semaphore = asyncio.Semaphore(config["max_concurrency"])

    total_personas = len(persona_prompts)
    completed_count = 0

    async def tracked_call(name, profile, prompt):
        nonlocal completed_count
        result = await call_backend_for_persona(
            prompt, user_message, name, config, semaphore,
            persona_profile=profile,
            adherence_prompt=adherence_prompt,
        )
        completed_count += 1
        status = "OK" if result["success"] else "FAIL"
        adherence = ""
        if result.get("adherence_score") is not None:
            adherence = f", adherence={result['adherence_score']}/10"
            if result.get("adherence_retried"):
                adherence += " (retried)"
        print(
            f"  [{completed_count}/{total_personas}] "
            f"{result['persona_name']}: {status} "
            f"({result['latency_ms']}ms{adherence})"
        )
        return result

    start_time = time.monotonic()
    tasks = [
        tracked_call(name, profile, prompt)
        for name, profile, prompt in persona_prompts
    ]
    api_results = await asyncio.gather(*tasks)
    total_elapsed_ms = int((time.monotonic() - start_time) * 1000)

    # Summary
    successful = sum(1 for r in api_results if r["success"])
    print(f"\nCompleted: {successful}/{len(api_results)} successful ({total_elapsed_ms}ms total)")

    # 6. Assemble results
    results = assemble_results(api_results, personas)
    failure_stage = None
    if results and len(results) < len(api_results):
        success_ratio = len(results) / len(api_results)
        if success_ratio < MIN_SUCCESS_RATIO:
            failure_stage = "insufficient_responses"
            print(
                f"ERROR: Only {len(results)}/{len(api_results)} personas succeeded "
                f"({success_ratio:.0%}). Minimum is {MIN_SUCCESS_RATIO:.0%}. "
                f"Analysis skipped.",
                file=sys.stderr,
            )
        else:
            print(
                f"WARNING: Partial results ({len(results)}/{len(api_results)} valid responses).",
                file=sys.stderr,
            )

    # 7. Save outputs
    overall_elapsed_ms = int((time.monotonic() - overall_start) * 1000)
    save_run_artifacts(
        config,
        results=results,
        api_results=api_results,
        total_elapsed_ms=overall_elapsed_ms,
        preflight_result=preflight_result,
        failure_stage=failure_stage,
    )

    if failure_stage == "insufficient_responses":
        return results

    if not results:
        print(
            "ERROR: No valid responses passed validation. Analysis was skipped.",
            file=sys.stderr,
        )

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Agent-Separated Survey Simulation Engine"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to survey config JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print first persona's prompt without calling API",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run analyze_results.py after simulation",
    )
    parser.add_argument(
        "--model",
        help="Override model for the selected backend",
    )
    parser.add_argument(
        "--backend",
        choices=BACKEND_CHOICES,
        help="Execution backend for persona simulation",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        help="Override max concurrency",
    )
    parser.add_argument(
        "--report-llm",
        action="store_true",
        help="Force LLM report generation (default for ask and concept-test).",
    )
    parser.add_argument(
        "--no-report-llm",
        action="store_true",
        help="Disable LLM report generation; use rule-based template report.",
    )
    parser.add_argument(
        "--report-backend",
        choices=REPORT_BACKEND_CHOICES,
        help="Backend for LLM report generation (`same` uses the simulation backend)",
    )
    parser.add_argument(
        "--no-adherence-check",
        action="store_true",
        help="Skip persona adherence checking (faster, cheaper)",
    )
    args = parser.parse_args()

    # Load config
    config_path = Path(args.config).resolve()
    if not config_path.exists():
        print(f"ERROR: Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = load_config(config_path)
    config["_config_path"] = str(config_path)
    config["_allowed_concept_options"] = extract_allowed_concept_options(
        config.get("variables", {}),
    )

    # Apply CLI overrides
    if args.model:
        config["model"] = args.model
    if args.backend:
        config["backend"] = args.backend
    if args.concurrency:
        config["max_concurrency"] = args.concurrency
    if args.report_backend:
        config["report_backend"] = args.report_backend
    if args.no_adherence_check:
        config["_no_adherence_check"] = True
    resolve_runtime_settings(config)

    # Run simulation
    results = asyncio.run(run_simulation(config, dry_run=args.dry_run))

    if args.dry_run:
        return

    if not results:
        sys.exit(1)

    # Optionally run analysis
    if args.analyze and results:
        import subprocess

        output_dir = config["_output_dir"]
        results_path = output_dir / "results.json"
        analyze_script = SKILL_DIR / "scripts" / "analyze_results.py"

        # Map survey_type to analyze_results.py types
        analyze_type_map = {
            "concept-test": "concept-test",
            "brand-map": "brand-map",
            "price-test": "price-test",
            "usage-habits": "usage-habits",
            "survey": "survey",
            "ask": "ask",
        }
        analyze_type = analyze_type_map.get(config["survey_type"], "survey")

        # Default LLM report ON for ask/concept-test when a usable backend is available.
        # Users can force-disable with --no-report-llm or force-enable with --report-llm.
        llm_eligible_types = {"ask", "concept-test"}
        use_llm_report = args.report_llm
        if not args.no_report_llm and analyze_type in llm_eligible_types:
            resolved_report_backend = config["_resolved_report_backend"]
            if resolved_report_backend != "python":
                use_llm_report = True
                print(
                    f"Using LLM report generation for {analyze_type} "
                    f"(pass --no-report-llm to fall back to template)."
                )

        print(f"\nRunning analysis: {analyze_type}...")
        analyze_cmd = [
            sys.executable,
            str(analyze_script),
            "--input",
            str(results_path),
            "--survey-type",
            analyze_type,
            "--backend",
            config["_resolved_backend"],
            "--report-backend",
            config["_resolved_report_backend"],
        ]
        if use_llm_report:
            analyze_cmd.append("--report-llm")
            if config.get("_resolved_report_model"):
                analyze_cmd.extend(["--model", config["_resolved_report_model"]])
        if config.get("topic"):
            analyze_cmd.extend(["--topic", config["topic"]])
        subprocess.run(analyze_cmd, check=True)

    # Final summary
    if results:
        print(f"\nDone. {len(results)} responses saved.")
        print(f"Output: {config['_output_dir']}")


if __name__ == "__main__":
    main()
