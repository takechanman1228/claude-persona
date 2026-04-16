# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code skill (`/persona`) inspired by TinyTroupe that builds market-specific persona panels and pressure-tests product concepts before fieldwork. It generates diverse personas, simulates independent concept test responses via `claude -p` subprocesses (one per persona), analyzes results, and produces executive reports.

## Common Commands

```bash
# Run all tests (120 unit tests, no external dependencies needed)
python -m pytest tests/ -q

# Run a single test file
python -m pytest tests/test_simulate_survey.py -q

# Run a single test
python -m pytest tests/test_simulate_survey.py::ValidateResponseTests::test_accepts_canonical_nested_concept_response -q

# Run survey simulation (requires claude CLI authenticated)
python scripts/simulate_survey.py --config demo/running-shoes/concept-test/config.json

# Dry-run (preview prompts without executing)
python scripts/simulate_survey.py --config demo/running-shoes/concept-test/config.json --dry-run

# Run with analysis + LLM report
python scripts/simulate_survey.py --config demo/running-shoes/concept-test/config.json --analyze --report-llm

# Run analysis only on existing results
python scripts/analyze_results.py --input outputs/.../results.json --survey-type concept-test

# Install analysis dependencies (only needed for analyze_results.py)
pip install pandas matplotlib seaborn
```

## Architecture

### 3-Step Workflow (maps to TinyTroupe)

| Step | Skill | TinyTroupe equivalent |
|------|-------|----------------------|
| 1. Build Panel | Panel Builder generates diverse personas | TinyPersonFactory |
| 2. Run Concept Test | Simulation Engine runs agent-separated interviews | TinyWorld |
| 3. Review Findings | Analysis Pipeline produces report + charts | Extract & Analyze |

### Three-Script Engine

All runtime logic lives in `scripts/`. There is no `src/` package — scripts import each other via `sys.path` manipulation.

1. **`simulate_survey.py`** (1500 lines) — The main entry point. Loads config JSON, loads personas from `panel_dir`, builds per-persona prompts from templates, fans out parallel `claude -p` subprocesses, validates JSON responses, retries failures, and saves `results.json` + `run_metadata.json`.

2. **`analyze_results.py`** (1400 lines) — Reads `results.json`, normalizes response structures, generates CSV exports, cross-tabulations, charts (matplotlib/seaborn), and a markdown report. Can use an LLM backend for narrative report generation or fall back to deterministic Python templates.

3. **`llm_backends.py`** (440 lines) — Backend abstraction for `claude-cli` and `codex-cli`. Handles CLI command construction, async/sync subprocess communication, JSON extraction from raw text, and model resolution. The `"auto"` backend infers which CLI is available via environment markers.

4. **`validate_panel.py`** (663 lines) — Panel quality gate. Runs 11 checks against a generated panel: count vs. requested, name uniqueness, segment balance, occupation/surname diversity, geo spread, age spread, gender distribution, Big Five cosine similarity (flags pairs ≥ 0.98), and slot-plan adherence. Returns structured JSON via `--json`; exits non-zero on any hard fail. Called automatically after panel generation; can also be run standalone for diagnosis.

### Data Flow

```
Config JSON (e.g., demo/running-shoes/concept-test/config.json)
    ↓ specifies survey_type, panel_dir, variables, backend
Persona JSONs (personas/{survey-id}/*.json + manifest.json)
    ↓ loaded via manifest.json's persona_files list
Profile Extraction (full ~300-line persona → ~40-line simulation profile)
    ↓ topic-relevant fields selected, verbose fields dropped
Per-Persona Prompt (simulation-prompt.md + template + profile + variables)
    ↓ each persona gets independent claude -p subprocess
Response Validation (validate_response checks required keys per survey type)
    ↓ retries up to 3 times on validation failure
results.json + run_metadata.json (outputs/{date}/{time}/{survey_type}/)
    ↓ analyze_results.py
report.md, results.csv, summary.json, charts (same output dir)
```

### Config JSON Structure

```json
{
  "survey_type": "concept-test",
  "panel_dir": "personas/{survey-id}",
  "topic": "Research topic",
  "variables": { "category": "...", "concepts": "..." },
  "output_dir": "outputs/...",
  "backend": "claude-cli|codex-cli|auto",
  "model": "sonnet",
  "max_concurrency": 5
}
```

The `variables` dict gets substituted into survey templates via `{{key}}` placeholders. The primary variable for concept-test is `concepts`.

Note: The engine internally supports additional survey types (brand-map, price-test, usage-habits, survey) but the public v1 surface exposes only `concept-test` and `generate`.

The `--market` option (default: `us`) controls persona geography. The SKILL.md orchestrator passes the resolved market name as `{{market}}` to generation prompt templates, which instruct the LLM to use local names, cities, currency, and cultural behaviors. The manifest.json stores the market for panel reuse matching.

### Persona Panel Structure

Each panel lives in `personas/{survey-id}/` with a `manifest.json` that lists `persona_files`. Individual persona JSONs follow the schema in `references/persona-schema.md` — nested under a `persona` top-level key with fields like `name`, `age`, `occupation`, `personality.big_five`, `style`, `preferences`, etc.

The `segment` and `segment_id` fields sit at the top level (sibling to `persona`), not nested inside it.

### Survey Templates

Templates in `templates/` define survey questions with `{{variable}}` placeholders. Each survey type maps to a specific template file via `SURVEY_TYPE_MAP` in `simulate_survey.py`. The template content gets substituted into the simulation prompt's `{SURVEY_QUESTIONS}` placeholder.

### Response Validation

`validate_response()` in `simulate_survey.py` enforces survey-type-specific required keys (defined in `REQUIRED_RESPONSE_KEYS`). All responses must be nested inside a `responses` dict — top-level response keys are rejected. `analyze_results.py` has a `normalize_result_entry()` that handles legacy top-level format for backward compatibility during analysis.

### Test Structure

Tests use `unittest` with a custom `load_module()` helper that imports scripts via `importlib.util.spec_from_file_location` (since scripts aren't a proper package). Tests cover validation logic, response normalization, cross-tab correctness, backend resolution, and persona schema validation against demo fixtures.

## Key Conventions

- **Canonical output format**: Results are always `[{"name": "...", "segment": "...", "age": N, "gender": "...", "occupation": "...", "responses": {...}}]`
- **Backend default model**: `claude-cli` defaults to `"sonnet"`; `codex-cli` has no default model
- **Profile extraction**: Full personas are compressed before simulation via `extract_simulation_profile()` — keeps response-driving fields (Big Five, style, topic-relevant interests) and drops verbose biography
- **Prompt construction**: `build_single_persona_prompt()` transforms the multi-persona `simulation-prompt.md` template into single-persona format at runtime via string replacements
- **`references/`** contains prompt templates and schema docs read by both the skill orchestrator (SKILL.md) and the Python scripts — treat these as the source of truth for prompt engineering
