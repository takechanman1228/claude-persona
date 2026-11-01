#!/usr/bin/env python3
"""Render the Claude Code SKILL.md as an OpenCode skill.

The Claude skill stays the single source of truth; this applies a handful of
string rewrites (backend, script paths, model notes) at install time.

    python3 opencode/port_skill.py SRC_SKILL_MD SKILL_DIR > SKILL.md
"""

from __future__ import annotations

import re
import sys

MODEL_SECTION = """#### Model Selection

Persona calls use OpenCode's configured default model (local models work, no
internet required). To pin a model, set `"model": "provider/model"` in the
config (e.g. `"ollama/qwen3:14b"`) or pass `--model provider/model`. Bare Claude
aliases such as `sonnet` are ignored on this backend. `report_model` works the
same way; `fallback_model`, `effort`, `max_budget_usd_per_call`, and
`structured_output` are Claude-only and ignored. JSON shape is enforced by the
prompt plus `validate_response()` retries, so prefer models that follow
instructions well. Run metadata records tokens and cost as reported by OpenCode.

"""

PREAMBLE = """
> **OpenCode port.** Skill directory: `{skill_dir}`. Every relative
> `scripts/`, `references/`, `templates/`, and `demo/` path below is inside
> that directory; `personas/` and `outputs/` go in the user's current
> working directory. Run scripts with `python3 {skill_dir}/scripts/...`.
> Each persona answers in its own `opencode run` subprocess (no tools, no
> project context), so always pass `--backend opencode-cli`. Everything runs
> offline — never try to fetch packages or web content.
"""


def port(text: str, skill_dir: str) -> str:
    # Frontmatter: drop Claude-only keys, retarget compatibility.
    text = re.sub(r"^argument-hint:.*\n", "", text, flags=re.M)
    text = re.sub(r"^user-invokable:.*\n", "", text, flags=re.M)
    text = text.replace("compatibility: claude-code", "compatibility: opencode")

    # Preamble right after the first H1.
    text = re.sub(r"(^# .*\n)", lambda m: m.group(1) + PREAMBLE.format(skill_dir=skill_dir),
                  text, count=1, flags=re.M)

    # Model section → OpenCode model notes.
    text = re.sub(r"#### Model Selection\n.*?(?=\*\*Why agent-separated\*\*)",
                  lambda m: MODEL_SECTION, text, count=1, flags=re.S)

    replacements = [
        ("python scripts/", f"python3 {skill_dir}/scripts/"),
        ("claude-cli", "opencode-cli"),
        ("`claude -p`", "`opencode run`"),
        ("`claude` CLI", "`opencode` CLI"),
        ('  "model": "sonnet",\n', ""),
        ("Claude CLI not authenticated or rate-limited",
         "No OpenCode model/provider configured, or local model server down"),
        ("Run `claude` interactively first to confirm auth; check rate limits",
         "Run `opencode run hello` to confirm a model/provider is configured"),
        ("check network", "check the provider (e.g. local Ollama server) is running"),
        ("this Claude wrapper", "this OpenCode wrapper"),
        ("Claude reads `results.json`", "The agent reads `results.json`"),
        ("`pip install pandas matplotlib seaborn`",
         "Install from a local wheelhouse: `./install-opencode.sh --wheels DIR`"),
        ("~/.claude/skills/persona/", f"{skill_dir}/"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    src, skill_dir = sys.argv[1], sys.argv[2].rstrip("/")
    with open(src, encoding="utf-8") as fh:
        sys.stdout.write(port(fh.read(), skill_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
