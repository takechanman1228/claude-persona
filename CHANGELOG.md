# Changelog

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
