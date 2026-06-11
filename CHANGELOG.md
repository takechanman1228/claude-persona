# Changelog

## [0.2.0] - 2026-06-11

Refresh for Claude Code CLI 2.1.x and the Claude Fable 5 model family.
All new CLI flags are capability-detected (`claude --help` is probed once
per process), so older CLI versions automatically degrade to the exact
0.1.0 command line.

### Features
- **Structured outputs** (`--json-schema`): persona responses are now
  validated server-side against the per-survey-type JSON schema and
  returned as a parsed `structured_output` object. Eliminates JSON
  extraction failures and validation retries (typical runs now complete
  with `attempts: 1` for every persona). Costs ~+1.8k input tokens per
  call; offset by removed retry round-trips. Opt out per run with
  `--no-structured-output` or `"structured_output": false`.
- **Context isolation** (`--safe-mode`): persona subprocesses and LLM
  report calls no longer load CLAUDE.md files, plugins, hooks, or skills
  from the surrounding environment — extending the agent-separation
  bias guarantee to the user's own project context. Opt out with
  `--no-isolation` or `"isolation": false`.
- **Cost and exact model attribution**: `run_metadata.json` is now
  `schema_version: 3` (additive) with `total_cost_usd`,
  `actual_model_ids` (the full model IDs that actually served the
  calls, e.g. `claude-sonnet-4-6` — `resolved_model` keeps the
  requested alias), per-persona `cost_usd`, cache token totals
  (`total_cache_creation_input_tokens` / `total_cache_read_input_tokens`),
  and the resolved `runtime_options`. Pre-0.2.0 metadata recorded only
  the alias. Token accounting now also accumulates across validation
  retries and adherence/regeneration calls instead of keeping only the
  last attempt.
- **Model strategy knobs** (all optional config keys / CLI flags):
  `"fallback_model"` / `--fallback-model` (automatic fallback when the
  primary model is overloaded — recommended pairing for `fable`/`opus`
  fan-outs), `"effort"` / `--effort` (low/medium/high/xhigh/max; not
  supported by haiku), `"max_budget_usd_per_call"` (per-subprocess hard
  cost cap). Claude Fable 5 works via `--model fable` or
  `"model": "fable"`; the default simulation model remains `sonnet`.
- `analyze_results.py` accepts `--no-isolation` and `--effort` for the
  LLM report call; `simulate_survey.py --analyze` forwards them.
- New example config: `configs/running-shoes-fable-concept-test.json`
  (fable fan-out with sonnet fallback and a per-call budget cap).
- **Demos regenerated on `claude-sonnet-4-6`** with the 0.2.0 engine —
  every published demo result now carries exact model attribution and
  cost in its `run_metadata.json`, and demo READMEs match the committed
  results. New `docs/MODEL-COMPARISON.md` documents result stability
  across three model generations (84–100% persona-level agreement;
  zero winner changes).

### Compatibility
- No breaking changes to the config contract; every new key defaults to
  prior behavior. Existing `run_metadata.json` consumers are unaffected
  (all new metadata fields are additive).
- Verified against Claude Code CLI 2.1.173. The legacy flag set
  (`--output-format json --tools "" --no-session-persistence`) is
  unchanged and still used on older CLIs.

## [0.1.0] - 2026-04-21

Initial public pre-release. Versioning corrected from the previously
tagged 1.0.0 / 1.1.0 internal milestones, which were never published
as a GitHub Release. All notes below describe the functionality that
ships in this first pre-release.

### Features
- Agent-separated persona simulation via `claude -p` subprocesses
  (one isolated context per persona) with up to 3 validation retries.
- Public survey surface: `concept-test`, `generate`, and `ask`.
- Panel generation with market-specific personas (`--market` option)
  and `validate_panel.py` quality gate (11 checks: count, name
  uniqueness, segment balance, occupation/surname diversity, geo
  spread, age spread, gender distribution, Big Five cosine similarity,
  slot-plan adherence).
- Analysis pipeline (`analyze_results.py`): CSV exports,
  cross-tabulations, charts (matplotlib/seaborn), and markdown
  reports.
- Survey-type-specific LLM report prompts:
  - `ASK_REPORT_SYSTEM_PROMPT` — Direct Answer, Where They Agreed /
    Differed, semantically-clustered Top Signals, no-occurrence
    emotion observations.
  - `CONCEPT_TEST_REPORT_SYSTEM_PROMPT` — Preference Verdict,
    Segment / Profile Splits, Purchase-Intent Drivers, cross-persona
    Per-Concept Strengths & Weaknesses, clustered Improvement Themes.
  - `GENERIC_REPORT_SYSTEM_PROMPT` retained as fallback for other
    survey types.
- `simulate_survey.py --analyze` defaults to LLM-based `report.md`
  for `ask` and `concept-test` when running on `claude-cli`; pass
  `--no-report-llm` to force the rule-based template.
- Rule-based report truncation relaxed and made sentence-aware
  (verbatims 240 → 600, ask short answers 200 → 400, concept
  reasoning 320 → 600, concept improvements 180/220 → 300/400).
- Rich synthesis demo reports for `running-shoes`, `genz-skincare`,
  and `japan-meeting-ai`.
- Installer scripts (`install.sh`, `install.ps1`) and plugin /
  marketplace manifests for `/plugin marketplace add`.

### Known limitations
- Public survey surface is limited to `concept-test`, `generate`, and
  `ask`. The engine internally supports `brand-map`, `price-test`,
  `usage-habits`, and `survey`, but these are not exposed in v0.1.0.
