#!/usr/bin/env python3
"""
Shared LLM backend adapters for Claude and Codex CLIs.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

BACKEND_CHOICES = ("auto", "claude-cli", "codex-cli")
REPORT_BACKEND_CHOICES = ("same", "python", "claude-cli", "codex-cli")

CODEX_ENV_MARKERS = ("CODEX_THREAD_ID", "CODEX_CI")
CLAUDE_ENV_MARKERS = (
    "CLAUDECODE",
    "CLAUDE_CODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_PROJECT_DIR",
    "CLAUDE_SESSION_ID",
    "CLAUDE_CODE_SIMPLE",
)


def _backend_command(backend: str) -> str:
    if backend == "claude-cli":
        return "claude"
    if backend == "codex-cli":
        return "codex"
    raise ValueError(f"Unsupported backend: {backend}")


def backend_available(backend: str) -> bool:
    """Return True when the corresponding CLI is available on PATH."""
    return shutil.which(_backend_command(backend)) is not None


def infer_backend_from_env(env: dict[str, str] | None = None) -> str | None:
    """Infer runtime backend from environment markers when possible."""
    env = env or os.environ
    if any(env.get(key) for key in CODEX_ENV_MARKERS):
        return "codex-cli"
    if any(env.get(key) for key in CLAUDE_ENV_MARKERS):
        return "claude-cli"
    return None


def resolve_backend(requested: str | None = None, env: dict[str, str] | None = None) -> str:
    """Resolve auto/explicit backend selection to a concrete CLI."""
    backend = (requested or "auto").strip()
    if backend not in BACKEND_CHOICES:
        raise ValueError(f"Unknown backend: {backend}. Valid: {BACKEND_CHOICES}")

    if backend != "auto":
        if not backend_available(backend):
            raise FileNotFoundError(
                f"Requested backend is not available on PATH: {_backend_command(backend)}"
            )
        return backend

    inferred = infer_backend_from_env(env=env)
    if inferred and backend_available(inferred):
        return inferred

    for candidate in ("claude-cli", "codex-cli"):
        if backend_available(candidate):
            return candidate

    raise FileNotFoundError("Neither `claude` nor `codex` CLI is available on PATH")


def resolve_report_backend(requested: str | None, simulation_backend: str) -> str:
    """Resolve the report backend, allowing `same` and deterministic Python fallback."""
    backend = (requested or "same").strip()
    if backend not in REPORT_BACKEND_CHOICES:
        raise ValueError(
            f"Unknown report backend: {backend}. Valid: {REPORT_BACKEND_CHOICES}"
        )
    if backend == "same":
        return simulation_backend
    return backend


def default_model_for_backend(backend: str) -> str | None:
    """Return backend-specific default model alias, if any."""
    if backend == "claude-cli":
        return "sonnet"
    return None


def resolve_model(model: str | None, backend: str) -> str | None:
    """Resolve model override or backend default."""
    if model:
        return model
    return default_model_for_backend(backend)


def format_model_label(model: str | None) -> str:
    """Human-readable model label for logs."""
    return model or "(CLI default)"


def describe_backend(backend: str) -> str:
    """Human-readable backend description."""
    if backend == "claude-cli":
        return "claude CLI (independent context per persona)"
    if backend == "codex-cli":
        return "codex CLI (independent context per persona)"
    return backend


def build_json_only_schema(required_keys: list[str] | None = None) -> dict:
    """Build a minimal JSON schema that locks the top-level contract."""
    response_properties: dict[str, object] = {}
    if required_keys:
        for key in required_keys:
            response_properties[key] = {}

    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "responses": {
                "type": "object",
                "properties": response_properties,
                "additionalProperties": True,
            }
        },
        "required": ["responses"],
        "additionalProperties": False,
    }
    if required_keys:
        schema["properties"]["responses"]["required"] = required_keys
    return schema


def extract_json_from_text(text: str):
    """Extract a JSON value from raw text or fenced code blocks."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty response text")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    patterns = [
        r"```json\s*\n(.*?)```",
        r"```\s*\n(.*?)```",
        r"(\{.*\})",
        r"(\[.*\])",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            continue
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError(f"Could not extract valid JSON from response:\n{text[:500]}")


def build_codex_prompt(system_prompt: str, user_message: str, output_mode: str) -> str:
    """Combine system instructions and user message for Codex exec."""
    mode_instruction = {
        "json": "Return only a JSON object that matches the provided schema exactly.",
        "text": "Return only the requested final text. Do not wrap it in code fences.",
    }.get(output_mode, "Return only the requested final output.")

    return (
        "You are being called through a non-interactive CLI adapter.\n"
        "Treat the SYSTEM PROMPT section as higher priority than the USER MESSAGE section.\n"
        "Do not ask clarifying questions. Do not inspect local files unless absolutely necessary.\n"
        f"{mode_instruction}\n\n"
        "<SYSTEM_PROMPT>\n"
        f"{system_prompt}\n"
        "</SYSTEM_PROMPT>\n\n"
        "<USER_MESSAGE>\n"
        f"{user_message}\n"
        "</USER_MESSAGE>\n"
    )


# Optional claude CLI flags introduced after the original release. Each is
# emitted only when the installed CLI advertises it, so older CLIs keep the
# legacy command line unchanged.
CLAUDE_CAPABILITY_FLAGS = (
    "--json-schema",
    "--safe-mode",
    "--fallback-model",
    "--effort",
    "--max-budget-usd",
)

_claude_capabilities_cache: dict[str, bool] | None = None


def detect_claude_capabilities(help_text: str | None = None) -> dict[str, bool]:
    """Detect which optional claude CLI flags this installation supports.

    Runs `claude --help` once per process and caches the result. Pass
    `help_text` to parse a known help output instead (used by tests).
    """
    global _claude_capabilities_cache
    if help_text is not None:
        return {flag: flag in help_text for flag in CLAUDE_CAPABILITY_FLAGS}
    if _claude_capabilities_cache is None:
        try:
            proc = subprocess.run(
                ["claude", "--help"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            detected = proc.stdout or ""
        except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
            detected = ""
        _claude_capabilities_cache = {
            flag: flag in detected for flag in CLAUDE_CAPABILITY_FLAGS
        }
    return _claude_capabilities_cache


def _build_claude_print_command(
    system_prompt: str,
    model: str | None = None,
    json_schema: dict | None = None,
    isolation: bool = True,
    fallback_model: str | None = None,
    effort: str | None = None,
    max_budget_usd: float | None = None,
    capabilities: dict[str, bool] | None = None,
) -> list[str]:
    """Build the claude -p command, gating newer flags on CLI capabilities."""
    caps = capabilities if capabilities is not None else detect_claude_capabilities()
    cmd = [
        "claude",
        "-p",
        "--system-prompt",
        system_prompt,
        "--output-format",
        "json",
        "--tools",
        "",
        "--no-session-persistence",
    ]
    if isolation and caps.get("--safe-mode"):
        cmd.append("--safe-mode")
    if json_schema is not None and caps.get("--json-schema"):
        cmd.extend(["--json-schema", json.dumps(json_schema)])
    if fallback_model and caps.get("--fallback-model"):
        cmd.extend(["--fallback-model", fallback_model])
    if effort and caps.get("--effort"):
        cmd.extend(["--effort", effort])
    if max_budget_usd is not None and caps.get("--max-budget-usd"):
        cmd.extend(["--max-budget-usd", str(max_budget_usd)])
    if model:
        cmd.extend(["--model", model])
    return cmd


def _parse_claude_envelope(stdout: str) -> dict:
    """Parse the claude -p --output-format json envelope defensively.

    With --json-schema the CLI leaves `result` empty and returns the parsed
    object in a separate top-level `structured_output` key, so both fields
    are surfaced and the caller picks whichever is populated.
    """
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"claude CLI returned non-JSON output: {stdout.strip()[:1000]}"
        ) from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected claude CLI payload: {str(payload)[:1000]}")
    if payload.get("is_error"):
        detail = payload.get("result") or payload.get("subtype") or "unknown error"
        raise RuntimeError(f"claude CLI reported an error: {str(detail)[:1000]}")

    usage = payload.get("usage") or {}
    return {
        "text": payload.get("result") or "",
        "structured": payload.get("structured_output"),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        "total_cost_usd": payload.get("total_cost_usd"),
        "model_usage": payload.get("modelUsage") or {},
    }


def preview_command(
    backend: str,
    model: str | None = None,
    structured_output: bool = False,
    isolation: bool = True,
    fallback_model: str | None = None,
    effort: str | None = None,
    capabilities: dict[str, bool] | None = None,
) -> str:
    """Render a backend command preview for dry-run output."""
    if backend == "claude-cli":
        caps = capabilities if capabilities is not None else detect_claude_capabilities()
        lines = [
            "claude -p \\",
            '  --system-prompt "..." \\',
            "  --output-format json \\",
            '  --tools "" \\',
            "  --no-session-persistence \\",
        ]
        if isolation and caps.get("--safe-mode"):
            lines.append("  --safe-mode \\")
        if structured_output and caps.get("--json-schema"):
            lines.append("  --json-schema '{...}' \\")
        if fallback_model and caps.get("--fallback-model"):
            lines.append(f"  --fallback-model {fallback_model} \\")
        if effort and caps.get("--effort"):
            lines.append(f"  --effort {effort} \\")
        if model:
            lines.append(f"  --model {model}")
        return "\n".join(lines)

    lines = [
        "codex -a never -s read-only \\",
    ]
    if model:
        lines.append(f"  -m {model} \\")
    lines.extend(
        [
            "  exec \\",
            "  --skip-git-repo-check \\",
            "  --ephemeral \\",
        ]
    )
    if structured_output:
        lines.extend(
            [
                "  --output-schema /tmp/schema.json \\",
                "  -o /tmp/response.json \\",
            ]
        )
    else:
        lines.append("  -o /tmp/response.txt \\")
    lines.append("  -")
    return "\n".join(lines)


async def _communicate_async(
    cmd: list[str],
    stdin_text: str,
    cwd: Path | None = None,
    timeout_s: int = 300,
) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd) if cwd else None,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=stdin_text.encode()),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError as error:
        proc.kill()
        await proc.communicate()
        raise TimeoutError(f"Command timed out after {timeout_s}s: {' '.join(cmd[:4])}") from error

    return proc.returncode, stdout.decode(), stderr.decode()


def _communicate_sync(
    cmd: list[str],
    stdin_text: str,
    cwd: Path | None = None,
    timeout_s: int = 300,
) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(cwd) if cwd else None,
        )
    except subprocess.TimeoutExpired as error:
        raise TimeoutError(f"Command timed out after {timeout_s}s: {' '.join(cmd[:4])}") from error

    return proc.returncode, proc.stdout, proc.stderr


def _build_codex_exec_command(
    model: str | None,
    output_path: Path,
    schema_path: Path | None = None,
) -> list[str]:
    cmd = ["codex", "-a", "never", "-s", "read-only"]
    if model:
        cmd.extend(["-m", model])
    cmd.extend(["exec", "--skip-git-repo-check", "--ephemeral"])
    if schema_path is not None:
        cmd.extend(["--output-schema", str(schema_path)])
    cmd.extend(["-o", str(output_path), "-"])
    return cmd


async def run_json_completion_async(
    *,
    backend: str,
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    json_schema: dict | None = None,
    cwd: Path | None = None,
    timeout_s: int = 300,
    isolation: bool = True,
    structured_output: bool = True,
    fallback_model: str | None = None,
    effort: str | None = None,
    max_budget_usd: float | None = None,
) -> dict:
    """Run a single JSON completion against the resolved backend."""
    resolved_backend = resolve_backend(backend)
    resolved_model = resolve_model(model, resolved_backend)

    if resolved_backend == "claude-cli":
        claude_schema = json_schema if structured_output else None
        cmd = _build_claude_print_command(
            system_prompt,
            model=resolved_model,
            json_schema=claude_schema,
            isolation=isolation,
            fallback_model=fallback_model,
            effort=effort,
            max_budget_usd=max_budget_usd,
        )
        returncode, stdout, stderr = await _communicate_async(
            cmd, user_message, cwd=cwd, timeout_s=timeout_s
        )
        if returncode != 0 and claude_schema is not None and "schema" in (
            (stderr or stdout).lower()
        ):
            # Per-run degradation: if the CLI rejected this particular schema,
            # retry once without --json-schema and fall back to text extraction.
            cmd = _build_claude_print_command(
                system_prompt,
                model=resolved_model,
                isolation=isolation,
                fallback_model=fallback_model,
                effort=effort,
                max_budget_usd=max_budget_usd,
            )
            returncode, stdout, stderr = await _communicate_async(
                cmd, user_message, cwd=cwd, timeout_s=timeout_s
            )
        if returncode != 0:
            raise RuntimeError((stderr or stdout).strip()[:1000])

        envelope = _parse_claude_envelope(stdout)
        if envelope["structured"] is not None:
            data = envelope["structured"]
        else:
            data = extract_json_from_text(envelope["text"])
        return {
            "backend": resolved_backend,
            "resolved_model": resolved_model,
            "text": envelope["text"],
            "data": data,
            "input_tokens": envelope["input_tokens"],
            "output_tokens": envelope["output_tokens"],
            "cache_creation_input_tokens": envelope["cache_creation_input_tokens"],
            "cache_read_input_tokens": envelope["cache_read_input_tokens"],
            "total_cost_usd": envelope["total_cost_usd"],
            "model_usage": envelope["model_usage"],
            "usage_supported": True,
        }

    prompt = build_codex_prompt(system_prompt, user_message, output_mode="json")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        output_path = tmpdir_path / "response.json"
        schema_path = None
        if json_schema is not None:
            schema_path = tmpdir_path / "schema.json"
            schema_path.write_text(json.dumps(json_schema), encoding="utf-8")

        cmd = _build_codex_exec_command(
            model=resolved_model,
            output_path=output_path,
            schema_path=schema_path,
        )
        returncode, stdout, stderr = await _communicate_async(
            cmd, prompt, cwd=cwd, timeout_s=timeout_s
        )
        if returncode != 0:
            raise RuntimeError((stderr or stdout).strip()[:1000])

        text = output_path.read_text(encoding="utf-8").strip()
        return {
            "backend": resolved_backend,
            "resolved_model": resolved_model,
            "text": text,
            "data": extract_json_from_text(text),
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "total_cost_usd": None,
            "model_usage": {},
            "usage_supported": False,
        }


def run_text_completion(
    *,
    backend: str,
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    cwd: Path | None = None,
    timeout_s: int = 300,
    isolation: bool = True,
    fallback_model: str | None = None,
    effort: str | None = None,
    max_budget_usd: float | None = None,
) -> dict:
    """Run a single text completion against the resolved backend."""
    resolved_backend = resolve_backend(backend)
    resolved_model = resolve_model(model, resolved_backend)

    if resolved_backend == "claude-cli":
        cmd = _build_claude_print_command(
            system_prompt,
            model=resolved_model,
            isolation=isolation,
            fallback_model=fallback_model,
            effort=effort,
            max_budget_usd=max_budget_usd,
        )
        returncode, stdout, stderr = _communicate_sync(
            cmd, user_message, cwd=cwd, timeout_s=timeout_s
        )
        if returncode != 0:
            raise RuntimeError((stderr or stdout).strip()[:1000])

        envelope = _parse_claude_envelope(stdout)
        return {
            "backend": resolved_backend,
            "resolved_model": resolved_model,
            "text": envelope["text"],
            "input_tokens": envelope["input_tokens"],
            "output_tokens": envelope["output_tokens"],
            "cache_creation_input_tokens": envelope["cache_creation_input_tokens"],
            "cache_read_input_tokens": envelope["cache_read_input_tokens"],
            "total_cost_usd": envelope["total_cost_usd"],
            "model_usage": envelope["model_usage"],
            "usage_supported": True,
        }

    prompt = build_codex_prompt(system_prompt, user_message, output_mode="text")
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "response.txt"
        cmd = _build_codex_exec_command(model=resolved_model, output_path=output_path)
        returncode, stdout, stderr = _communicate_sync(
            cmd, prompt, cwd=cwd, timeout_s=timeout_s
        )
        if returncode != 0:
            raise RuntimeError((stderr or stdout).strip()[:1000])

        return {
            "backend": resolved_backend,
            "resolved_model": resolved_model,
            "text": output_path.read_text(encoding="utf-8"),
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "total_cost_usd": None,
            "model_usage": {},
            "usage_supported": False,
        }
