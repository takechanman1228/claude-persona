# Command Details

## `/persona ask [free text]`

**Purpose**: Ask an open-ended qualitative question to an existing persona panel.
Use this to explore motivations, barriers, language, emotional reactions, and
decision context — before or after a structured concept test.

`/persona ask` sits between `generate` and `concept-test`:
1. `/persona generate` — build a reusable panel
2. `/persona ask` — explore motivations and barriers
3. `/persona concept-test` — compare explicit options when ready

**User provides**:
- A freeform research question (required)
- (Optional) `--panel <survey-id>` — use a specific panel by ID
- (Optional) `--market MARKET` — market filter for auto-detection (default: us)

**Panel resolution**:
- If `--panel` given: load that panel directly
- Auto-detect: scan `personas/` for matching panels; choose best fit or ask if ambiguous
- If no panel exists: inform the user to run `/persona generate` first

**Output**:
- `results.json` — raw persona responses (`short_answer`, `reasoning`, `themes`, `emotion`)
- `summary.json` — signal counts, emotion distribution
- `report.md` — synthesis: direct answer, key findings, themes, verbatims
- `results.csv` — flat table

**Examples**:
```
/persona ask What frustrates you most about choosing a stroller online?
/persona ask Why would you ignore this skincare ad?
/persona ask What makes this product feel overpriced?
/persona ask Walk me through how you would decide whether to buy this.
/persona ask --panel running-footwear-us-15p-2026-04 Why would you skip this ad?
/persona ask --market japan What makes this feel like a premium product?
```

## `/persona concept-test [free text]`

**Purpose**: Compare concepts, messages, designs, or feature bundles with a persona panel.

Concept test is broadly defined — it covers any research where you put 2-4 options
in front of a panel and ask which one wins:

- Product concept A/B/C comparison
- Message or positioning A/B test
- Package design evaluation
- Competitive comparison
- Feature bundle prioritization
- Value framing with price context

**User provides** (via free text or interactively):
- Product category / topic
- 2-4 option descriptions (name + key features)
- (Optional) `--count N` for panel size
- (Optional) `--market MARKET` for target market (default: us)
- (Optional) `--segments` for segment-driven flow

**Output**:
- `results.json` — raw responses
- `report.md` — one-pager markdown report

**Examples**:
```
/persona concept-test Evaluate 3 new canned coffee concepts
/persona concept-test Compare 2 ad headlines for our protein bar
/persona concept-test --market japan Evaluate 3 new canned coffee concepts
/persona concept-test --count 8 EV purchase intent
/persona concept-test --segments Canned coffee
```

## `/persona generate`

**Purpose**: Generate and save persona files for reuse across studies.

**User provides**:
- Topic / product category
- (Optional) `--count N` (default: 5)
- (Optional) `--market MARKET` for target market (default: us)
- (Optional) `--segments` for segment-driven generation
- (Optional) Segment definitions (JSON or natural language)

**Output**: JSON files saved to `personas/{survey-id}/` directory with manifest.

## Engine Model & Reliability Options

The simulation engine (`scripts/simulate_survey.py`) accepts model and
reliability options on top of the command surface above. Defaults match
prior behavior; new claude CLI flags are capability-detected and skipped
on older CLI versions.

| Config key | CLI flag | Effect |
|------------|----------|--------|
| `"model"` | `--model` | Simulation model: `sonnet` (default), `haiku`, `opus`, `fable` (Claude Fable 5, ~4x sonnet cost), or a full model ID |
| `"report_model"` | — | Model for LLM report synthesis only (recommended: `"fable"` for the richest narrative at one extra call) |
| `"fallback_model"` | `--fallback-model` | Automatic fallback when the primary model is overloaded (comma-separated list allowed) |
| `"effort"` | `--effort` | `low`/`medium`/`high`/`xhigh`/`max`; not supported by haiku |
| `"max_budget_usd_per_call"` | — | Hard cost cap per persona subprocess |
| `"structured_output"` | `--no-structured-output` | Server-validated JSON via `--json-schema` (default on) |
| `"isolation"` | `--no-isolation` | Context isolation via `--safe-mode` (default on) |

Run metadata (`run_metadata.json`, schema_version 3) records `total_cost_usd`,
per-persona `cost_usd`, and `actual_model_ids` — the exact model IDs that
served the run, alongside the requested alias in `resolved_model`.
