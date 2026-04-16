---
name: persona
description: >
  Build a persona panel, explore customer motivations through open-ended
  questions, and pressure-test product concepts before spending on fieldwork.
  Generates diverse AI persona panels, runs agent-separated interviews
  (qualitative ask or structured concept test), analyzes results with
  theme synthesis, cross-tabs, and charts, and delivers executive research
  reports. Use when the user wants to ask a panel about motivations or
  barriers, which concept to launch, who to target first, which message
  resonates, whether a value proposition works, or needs a reusable
  persona panel.
argument-hint: "concept-test | generate | ask [free text]"
user-invokable: true
license: MIT
compatibility: claude-code
metadata:
  author: Hajime Takeda
  version: "0.1.0"
---

# AI Persona Panels for Customer Research

Build reusable persona panels, ask open-ended customer questions,
and run concept tests on messages, offers, and product ideas. 

## 3-Step Workflow

Inspired by TinyTroupe (Generate Personas → Simulate Interactions → Extract & Analyze):

| Step | What happens | Component |
|------|-------------|-----------|
| **1. Build Panel** | Define your market, generate diverse personas | Panel Builder |
| **2. Run Ask / Concept Test** | Each persona responds independently in its own subprocess | Simulation Engine |
| **3. Review Findings** | Structured report with themes, cross-tabs, charts, and verbatims | Analysis Pipeline |

Recommended workflow:
1. `/persona generate` — build a reusable panel
2. `/persona ask` — explore motivations, barriers, language, and decision criteria
3. `/persona concept-test` — compare explicit options when ready for a structured choice task

## Quality Guidelines

- **Take your time with persona generation.** Diverse, detailed personas are the foundation of useful results. Do not skip diversity verification.
- **Do not skip validation.** Always verify response JSON structure before proceeding to analysis.
- **Quality over speed.** A 5-persona panel with rich, differentiated responses is more valuable than a 15-persona panel with generic answers.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/persona generate Running shoe shoppers in the US` | Build a reusable panel (default 5 personas) |
| `/persona generate --count 10 Gen Z skincare shoppers in the US` | Panel with custom size |
| `/persona generate --segments Canned coffee drinkers in Japan` | Segment-driven panel (default 15) |
| `/persona ask What frustrates you most about choosing skincare products?` | Explore motivations and barriers |
| `/persona ask Why would you ignore an ad for a new running shoe?` | Qualitative reaction before concept test |
| `/persona concept-test Compare 3 running shoe concepts` | Concept test — concepts provided interactively |
| `/persona concept-test --market japan Evaluate 3 canned coffee concepts` | Concept test with Japanese panel |

`ask` explores open-ended motivations, barriers, and language.
`concept-test` covers any comparison research: product concepts, messaging A/B,
packaging, competitive comparisons, feature bundles, and value framing with
price context.

For detailed input requirements and output descriptions per command,
see `references/command-details.md`.

---

## Argument Parsing Rules

The text after the command is parsed as follows:

1. **Command** (required): `concept-test`, `generate`, `ask`
2. **Options** (optional):
   - `--count N` — Panel size (default: **5**; not applicable for `ask`)
   - `--market MARKET` — Target market/country (default: **us**). Accepts country codes (`us`, `japan`/`jp`, `uk`, `de`, `fr`, `cn`, `kr`) or freeform descriptors ("Southeast Asia", "urban Brazil"). Shorthand codes are expanded: `us` → United States, `japan`/`jp` → Japan, `uk` → United Kingdom, etc.
   - `--segments` — Activate segment-driven flow; default panel size becomes 15 (not applicable for `ask`)
   - `--panel PANEL` — (`ask` only) Specify the panel survey-id to use (e.g., `running-footwear-us-15p-2026-04`). Skips auto-detection.
3. **Free text** (optional): Everything else is the **research intent** — a natural language
   description of what the user wants to research. For `ask`, the free text is the question itself.

**Parsing examples**:
```
/persona concept-test Evaluate 3 new canned coffee concepts
  → type: concept-test, count: 5, intent: "Evaluate 3 new canned coffee concepts"

/persona concept-test --count 8 Compare ad headlines for EV launch
  → type: concept-test, count: 8, intent: "Compare ad headlines for EV launch"

/persona concept-test --segments Canned coffee
  → type: concept-test, count: 15, mode: segment-driven, intent: "Canned coffee"

/persona generate --count 15 Running shoes
  → type: generate, count: 15, market: "United States", intent: "Running shoes"

/persona generate --market japan --count 10 Canned coffee
  → type: generate, count: 10, market: "Japan", intent: "Canned coffee"

/persona concept-test --market japan Evaluate 3 new canned coffee concepts
  → type: concept-test, count: 5, market: "Japan", intent: "Evaluate 3 new canned coffee concepts"

/persona ask What frustrates you most about buying running shoes online?
  → type: ask, question: "What frustrates you most about buying running shoes online?", panel: auto-detect

/persona ask --panel running-footwear-us-15p-2026-04 Why would you ignore this ad?
  → type: ask, question: "Why would you ignore this ad?", panel: "running-footwear-us-15p-2026-04"

/persona ask --market japan What makes this product feel overpriced?
  → type: ask, question: "What makes this product feel overpriced?", market: "Japan", panel: auto-detect
```

**When free text is provided**:
- Extract the topic from the intent text
- Determine what information is still missing:
  - `concept-test`: concept/option details (names + descriptions) — ask only if not in intent
  - `ask`: the question is the free text; no additional info required
- If sufficient information is present, proceed without further questions

**When no free text is provided**:
- Collect all required information interactively (current behavior)

---

## Orchestration Logic

### Step 1: Build Panel

1. **Parse the user's request** to determine:
   - Command (concept-test or generate)
   - Free-text research intent (if provided)
   - Panel size (default: **5**; or 15 if `--segments`)
   - Market (default: **United States**; resolve shorthands like `jp` → Japan)
   - Mode: topic-only (default) or segment-driven (`--segments`)

2. **Collect missing info**:
   - Extract topic from free text (e.g., "Evaluate 3 new canned coffee concepts" → topic = "Canned coffee")
   - For concept-test: identify concept/option details — ask only if not provided
   - If free text provides sufficient context, skip interactive questions

3. **Persona Panel Decision**:

   a) **User explicit instruction**:
      - "Use existing panel" / "reuse {name}" → load from specified `personas/{survey-id}/` directory
      - "Generate new personas" or provides segment definitions → new generation
      - No instruction → proceed to auto-decision (b)

   b) **Auto-decision** (default is NEW generation):
      - Scan `personas/` for subdirectories containing `manifest.json` (ignore `_archive/`)
      - If a manifest's `category` closely matches the current topic AND `market` matches (or is absent, treated as "United States") → propose reuse, ask user
      - If no match found → proceed directly to new generation (no confirmation needed)

   c) **New generation flow — two modes**:

      **Topic-only mode** (default):
      - Skip segment inference entirely
      - Infer diversity dimensions inline and generate all N personas in one batch
      - See `references/topic-only-generation-flow.md` for the 4-step flow
        (dimension inference, target assignment, generation, manifest creation)
      - Do NOT ask user for segment approval — proceed directly

      **Segment-driven mode** (`--segments`):
      - If user provided segment definitions → use them directly
      - If topic only → run segment inference (see `references/segment-inference-prompt.md`)
        to generate 3-4 segments → present to user for approval
      - Default panel size: 15 personas (3 segments × 5 personas)
      - Follow the **4-step generation flow** below

      ### Segment-Driven 4-Step Generation Flow

      Inspired by TinyTroupe's TinyPersonFactory plan-based approach:
      instead of letting the LLM freely generate N personas per segment,
      first build a deterministic sampling plan, then generate each persona
      from its slot specification.

      **Step 1a: Deterministic Count Allocation**

      Compute per-segment counts deterministically — do NOT delegate count
      management to the LLM. This is the orchestrator's responsibility:

      1. `base = floor(count / num_segments)`
      2. `remainder = count mod num_segments`
      3. First `remainder` segments get `base + 1`; remaining get `base`
      4. **Verify**: `sum(segment_counts) == count` before proceeding

      Examples:
      - 30 ÷ 3 = 10 + 10 + 10
      - 17 ÷ 4 = 5 + 4 + 4 + 4
      - 8 ÷ 3 = 3 + 3 + 2

      Record each segment's allocated count. If the sum does not equal
      the requested count, fix the allocation before generating.

      **Step 1b: Sampling Plan Generation**

      Generate a sampling plan that assigns diversity attributes to each
      persona slot. See `references/sampling-plan-prompt.md` for the prompt.

      The plan is a JSON array with exactly N rows (one per persona).
      Each row specifies: segment, age_bucket, gender, occupation_tier,
      geography_type, region_hint, category_stance, ethnicity_hint.

      After the LLM returns the plan, verify:
      - `len(plan) == count`
      - Per-segment row counts match the allocation from Step 1a
      - If verification fails, regenerate the plan (max 2 attempts)

      **Step 1c: Persona Generation from Slot Specifications**

      Generate personas sequentially by segment. For each segment batch:

      1. Pass all slot rows for that segment to `persona-generation-prompt.md`
         as `{{slot_spec}}` — the LLM fleshes out each slot into a full persona
      2. Pass the **exclusion list** of already-used names, surnames, and
         occupation titles from previous segments as `{{exclusion_list}}`
      3. After generation, extract the names, surnames, and occupation titles
         from the generated personas and add them to the exclusion list
         for the next segment

      This ensures cross-segment duplicate suppression is built into the
      generation flow, not left to chance.

      **Step 1d: Panel Validation**

      After all personas are generated, run `scripts/validate_panel.py`
      programmatically:

      ```bash
      python scripts/validate_panel.py --panel-dir personas/{survey-id} --requested-count {count} --json
      ```

      Interpret the results:
      - **Hard fails** (severity: "fail"): The panel has a contract violation.
        Attempt to fix the specific issue (e.g., regenerate a duplicate-named
        persona) and re-validate. Max 2 retry cycles.
      - **Warnings** (severity: "warning"): Note them but do not block.
      - If hard fails persist after retries, present the panel with
        warnings and let the user decide.

   d) **Panel confirmation with QA summary**:
      - Present the panel overview table:
        ```
        | # | Name | Age | Gender | Occupation | Segment |
        |---|------|-----|--------|------------|---------|
        | 1 | Marcus Chen | 34 | M | Software Engineer | Serious Runners |
        | 2 | Diana Okafor | 52 | F | School Principal | Casual Joggers |
        | 3 | Jake Morales | 23 | M | Barista / Student | Fashion-Conscious |
        ```
      - Below the table, show a **QA Summary** from validate_panel results:
        ```
        ### Panel QA
        - Count: 30/30 ✓
        - Segment balance: Serious (10), Casual (10), Fashion (10) ✓
        - Names: all unique ✓
        - Occupation duplicates: none ✓
        - Age spread: OK ✓
        - Gender balance: OK ✓
        - Big Five near-duplicates: 1 pair (0.985) ⚠
        ```
      - If any hard fail remains, flag it prominently and offer to
        regenerate the affected personas
      - After user approves → proceed to concept test execution

   e) **Save personas**:
      - Save each persona as `personas/{survey-id}/{Name_Underscored}.json`
      - Create `manifest.json` with:
        - `"generation_mode": "topic-only"` or `"segment-driven"`
        - `"market": "{resolved market name}"`
        - `"requested_count": {count}`
        - `"sampling_plan": [...]` (the slot specifications from Step 1b)
        - `"validation_report": {...}` (from validate_panel output)
        - All segments must include `"description"` field

4. **Load survey template** from `templates/concept_test.md`.

### Step 2: Run Concept Test

Read `references/simulation-prompt.md` for the core simulation prompt.

**Before simulation, extract simulation profiles** from the full persona JSONs
using `extract_simulation_profile()` in `scripts/simulate_survey.py`. Pass the compact
profiles (~40-50 lines/persona) as `{PERSONAS_JSON}` instead of the full personas
(~300 lines/persona). This saves context window while preserving all response-driving fields.

#### Agent-Separated Execution (Recommended)

Use `simulate_survey.py` for production-quality results. This wrapper must force
`--backend claude-cli`, which runs each persona in a fully independent
`claude -p` subprocess — zero inter-persona bias.

```bash
python scripts/simulate_survey.py --config {config-path} --backend claude-cli
```

How it works:
1. Builds a per-persona system prompt (simulation instructions + single persona profile + survey questions)
2. Launches parallel `claude -p` processes (controlled by `--concurrency`, default 5)
3. Each process uses `--output-format json --tools "" --no-session-persistence`
4. Parses JSON response, validates structure, retries on failure (up to 3 attempts)
5. Saves `results.json` + `run_metadata.json` to `config.output_dir` when provided, otherwise to `outputs/{YYYY-MM-DD}/{HHMMSS}/{survey_type}/`
6. Runs a backend preflight before persona fan-out; if it fails, stop immediately and record `failure_stage: "preflight"`

Options: `--dry-run`, `--analyze`, `--report-llm`, `--no-adherence-check`, `--model`, `--concurrency`, `--report-backend`

**Why agent-separated**: Shared-context simulation suffers from anchoring bias,
consensus bias, and style contamination. Agent separation eliminates all three.

**Error handling**: If `simulate_survey.py` exits non-zero, read `run_metadata.json`
for `failure_stage`, `preflight.error`, `per_persona[].error`, and
`per_persona[].validation_issues`. Common stages: `preflight` (backend unreachable),
`simulation` (persona subprocess failed), `validation` (response parsing failed).
Report the failure stage and the most relevant error payload before suggesting remediation.

The canonical persisted output format is:

```json
[
  {
    "name": "Persona Name",
    "segment": "Profile Label or Segment Name",
    "age": 35,
    "gender": "Female",
    "occupation": "Nurse",
    "responses": {
      "question_key": "answer"
    }
  }
]
```

### Step 3: Review Findings

1. Save canonical `results.json` + `run_metadata.json`
2. Run `scripts/analyze_results.py` immediately with `--analyze`
3. Generate `report.md` plus `results.csv` / `summary.json` and optional charts
4. Save to `config.output_dir` when provided, otherwise to `outputs/{YYYY-MM-DD}/{HHMMSS}/{survey_type}/`
5. Present a concise summary to the user with the report path
6. When this Claude wrapper requests an LLM report, keep `--report-backend same` so report generation also stays on `claude-cli`

**Report generation defaults**:
- `ask` and `concept-test` default to LLM-generated `report.md` when `--analyze` runs on a
  `claude-cli` backend. Each survey type uses a dedicated synthesis prompt
  (`ASK_REPORT_SYSTEM_PROMPT` / `CONCEPT_TEST_REPORT_SYSTEM_PROMPT` in
  `scripts/analyze_results.py`).
- Pass `--no-report-llm` to force the rule-based template report (faster / cheaper, but less rich).
- Other survey types (`brand-map`, `price-test`, `usage-habits`, `survey`) still default to the
  rule-based template; add `--report-llm` to opt into LLM synthesis.

**Report format**: See `references/report-template.md` for the baseline one-pager structure.
The survey-type-specific LLM prompts embed their own richer structures (Direct Answer, Where
They Agreed/Differed, Top Signals with clustering for ask; Preference Verdict, Segment Splits,
Per-Concept Strengths/Weaknesses, Improvement Theme Clusters for concept-test).

---

### Step: Run Ask (for `/persona ask` command)

`/persona ask` is a focused v1 addition that sits between `generate` and `concept-test`.
It lets users pose open-ended qualitative questions to an existing panel — no new panel
generation required. Each persona responds independently (agent-separated), and the
answers are synthesized into a usable research summary.

#### 1. Parse Command

Extract:
- **Question** (required): Everything after `/persona ask [options]` is the research question
- **Panel override** (optional): `--panel <survey-id>` — skip auto-detection
- **Market** (optional): `--market <market>` — used during auto-detection as a filter

If the user provides no question text, ask: "What would you like to ask the panel?"

#### 2. Resolve Panel (required for ask)

`/persona ask` always requires an existing panel. It never generates new personas.

**If `--panel` is given**:
- Load `personas/{PANEL}/manifest.json`
- If the directory does not exist, stop and report the error

**If no `--panel` given (auto-detect)**:
- Scan `personas/` for subdirectories containing `manifest.json` (exclude `_archive/`)
- If `--market` is given, filter candidates to those whose `manifest.market`
  matches (or whose market is absent, treated as "United States"). Drop non-matching panels.
- From remaining candidates:
  - If exactly one candidate: use it directly — no confirmation needed
  - If multiple candidates: present a numbered list with survey-id, category,
    market, and persona count, then ask the user to pick one
  - If no candidates: tell the user clearly and preserve their question:
    > "No persona panel found. Run `/persona generate {topic}` first, then re-run your ask."
    Do NOT silently generate a new panel.

Display the matched panel to the user before running:
```
Using panel: running-footwear-us-15p-2026-04 (15 personas, US)
```

#### 3. Build Ask Config

Construct a config JSON and save it to `outputs/{YYYY-MM-DD}/{HHMMSS}/ask/ask-config.json`:

```json
{
  "survey_type": "ask",
  "panel_dir": "personas/{matched-panel-id}",
  "topic": "{manifest.category}",
  "variables": {
    "category": "{manifest.category}",
    "user_question": "{user's question verbatim}"
  },
  "backend": "claude-cli",
  "model": "sonnet",
  "max_concurrency": 5
}
```

#### 4. Run Simulation

```bash
python scripts/simulate_survey.py --config {config-path} --analyze
```

The `--analyze` flag automatically runs `analyze_results.py --survey-type ask`,
which produces `summary.json` with pre-computed `top_signals`, `emotion_distribution`,
plus `report.md` with ask-specific sections.

Each persona receives the question via `templates/ask.md` and returns:
- `short_answer` — direct 2-3 sentence answer
- `reasoning` — concrete personal reasoning
- `themes` — 1-4 short theme phrases
- `emotion` — one-word dominant tone

#### 5. Present Ask Synthesis

After the run completes, an LLM-generated `report.md` already exists in the output
directory (produced by `analyze_results.py` using `ASK_REPORT_SYSTEM_PROMPT`). Your job
is to **read that report** plus `results.json` / `summary.json`, then:

1. **Verify report.md quality.** Check that it follows the expected structure:
   `Direct Answer` → `Key Findings` → `Where They Agreed` → `Where They Differed` →
   `Notable Verbatims` → `Top Signals` → `Emotion Distribution` → `Caveats`.
   If any section is missing or weak, overwrite `report.md` with your own synthesis
   using the template below.
2. **Present a concise summary to the user** — not the full report, just 5-8 lines
   covering the Direct Answer and top 2-3 findings. Always include the path to
   `report.md` so they can read the full document.

Use the pre-computed theme counts and emotion distribution from `summary.json` — do
not recompute them manually. When presenting the summary to the user, follow this structure:

```
## "{question}" — Panel Response Summary
**Panel**: {manifest_topic} ({N} personas, {market})
**Date**: {date}

### Direct Answer
[2-3 sentence synthesis of what the panel said overall, without attributing to
any single persona. Focus on the dominant response pattern.]

### Key Findings
1. [Primary theme or point of agreement]
2. [Secondary finding or notable split]
3. [Surprise, tension, or segment difference]

### Where They Agreed
[What most or all personas said in common]

### Where They Differed
[Notable splits — by age, segment, personality type, or circumstance]

### Notable Verbatims
> "[direct quote from reasoning field]" — Name, Age, Occupation

> "[direct quote]" — Name, Age, Occupation

### Top Signals
[comma-separated theme phrases with frequency counts, e.g.: "sizing uncertainty (8)", "brand trust (5)"]

---
Artifacts: outputs/{date}/{time}/ask/
*Virtual panel of {N} synthetic personas — directional signal only.*
```

**Important**: This is a qualitative synthesis, not a concept test. Do NOT frame
findings as preference shares or percentages unless emotion counts or theme counts
are clearly labeled as such.

---

### Step: Present Concept-Test Synthesis (for `/persona concept-test`)

Concept-test runs produce a structured choice (A/B/C) plus reasoning, purchase-likelihood
scores, and improvement suggestions. After `--analyze` finishes, an LLM-generated `report.md`
already exists in the output directory (produced via `CONCEPT_TEST_REPORT_SYSTEM_PROMPT`).
Your job as the orchestrator is to:

1. **Verify report.md quality.** Check that it follows this structure:
   `Preference Verdict` → `Key Findings` → `Segment / Profile Splits` →
   `Purchase-Intent Drivers` → `Per-Concept Strengths and Weaknesses` →
   `Improvement Theme Clusters` → `Notable Verbatims` → `Caveats`.
   If any section is missing or weak, overwrite `report.md` with your own synthesis
   using the template below.
2. **Present a concise summary to the user** — the verdict plus the 2-3 most actionable
   findings, not the full report. Always include the path to `report.md`.

Synthesis template to use when overwriting `report.md`:

```markdown
# Concept Test: {topic} — Virtual Research Report

**Date**: {date} | **Panel**: {N} personas

## Panel Overview
| # | Name | Age | Occupation | Profile | Preferred | Purchase Likelihood |
|---|------|-----|------------|---------|-----------|---------------------|
| 1 | ... | ... | ... | ... | ... | ... |

## Preference Verdict
[2-3 sentences. Leader + margin + confidence. Use "Clear winner" (>60%), "Narrow lead" (40-60%),
"No winner; tied" (ties), or "Fragmented" (every concept <40%). Include raw counts.]

## Key Findings
1. [Cross-persona insight]
2. [Second insight]
3. [Third insight]

## Segment / Profile Splits
[Who picked what. Organize by segment → preference → shared reason. 3-6 lines.]

## Purchase-Intent Drivers
[What moved `purchase_likelihood` up or down across the panel. Cite factors personas credited.]

## Per-Concept Strengths and Weaknesses
### Concept A — N/total chose this
**Strengths (cross-persona):** [synthesis, not per-chooser dump]
**Weaknesses (cross-persona):** [what passers flagged]

### Concept B — N/total chose this
[...]

## Improvement Theme Clusters
- **Cluster label** (N mentions across Concepts X, Y) — one-line gloss with 1-2 persona attributions
[3-6 clusters]

## Notable Verbatims
> "full sentence from reasoning field" — Name, Age, Occupation

> "another full sentence" — Name, Age, Occupation

## Caveats
- Virtual panel of {N} personas; directional only
- Not statistically representative; use for hypothesis generation
- AI-generated responses may exhibit positivity bias
```

**Important**: Synthesis over summary. Never write a "Profile Analysis" section with one paragraph
per persona — that is the old rule-based format. Never dump per-chooser verbatim reasoning under a
"Support reasons" list; always cluster across personas.

---

## Persona Schema

See `references/persona-schema.md` for the complete JSON schema.

Key principle: Personas must be detailed enough to produce differentiated,
realistic survey responses. The Big Five personality traits, communication style,
and lifestyle details are what drive response variation.

In topic-only mode, the `segment` field contains a persona-specific archetype label
(e.g., "Budget Pragmatist"). In segment-driven mode, it contains the shared segment
name (e.g., "Daily Ritual Drinker").

## Simulation Engine

See `references/simulation-prompt.md` for the core prompt template.

Key principles:
- Each persona's response must be deeply grounded in their profile
- Not all personas are positive or articulate — reflect real consumer diversity
- Big Five traits influence enthusiasm, skepticism, detail level, and decision style
- Education level affects vocabulary and expression complexity
- Some personas should give unexpected responses (break stereotype expectations)

## Survey Templates

The concept test template (`templates/concept_test.md`) handles A/B/C concept
evaluation with reasoning. It is flexible enough to cover product comparisons,
message A/B tests, packaging evaluations, competitive comparisons, and feature
bundle comparisons. For research that doesn't fit the template, the orchestrator
constructs custom questions from the user's brief.

The ask template (`templates/ask.md`) handles open-ended qualitative questions.
It elicits a direct answer, concrete reasoning, recurring signals, and emotional tone
— structured enough for synthesis without forcing a choice.

## Analysis Pipeline

**Default (topic-only)**: Claude reads `results.json` and generates `report.md` directly.

**`--analyze` flag**: Runs `scripts/analyze_results.py` for:
- JSON → CSV conversion
- Cross-tabulation (segment × response) or persona comparison table
- Chart generation (bar, stacked bar, heatmap)
- Summary statistics
- Markdown report generation (`--report-only` skips charts)

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `claude -p` subprocess hangs | Claude CLI not authenticated or rate-limited | Run `claude` interactively first to confirm auth; check rate limits |
| `failure_stage: "preflight"` in metadata | Backend unreachable before persona fan-out | Verify `claude` CLI is installed and on PATH; check network |
| All personas give identical responses | Shared-context mode used instead of agent-separated | Always use `simulate_survey.py --backend claude-cli` |
| `ModuleNotFoundError: pandas` | Python dependencies not installed | `pip install pandas matplotlib seaborn` (needed for analysis only) |
| Persona panel lacks diversity | Panel size too small or topic too narrow | Increase `--count`; broaden topic description; check generation prompt output |
| `validate_response` failures / retries | LLM returned wrong JSON shape | Script retries up to 3 times automatically; if persistent, check survey template keys |
| Report missing charts | `--report-only` flag was used, or matplotlib not installed | Re-run without `--report-only`; install matplotlib |
| Panel validation hard fails | Count mismatch, duplicate names, missing metadata | Run `python scripts/validate_panel.py --panel-dir {dir}` to diagnose; fix specific issues and re-validate |
| Panel validation warnings | Occupation/surname duplicates, age clustering, Big Five similarity | Warnings don't block usage; consider regenerating specific personas for higher quality |

## File Organization

**Skill directory** (installed to `~/.claude/skills/persona/`): `references/`, `scripts/`,
`templates/`, `demo/` — read-only assets, never modified during execution.

**User's project directory** (CWD): `personas/` (generated panels), `outputs/` (results,
reports, charts). All generated data is saved to the user's current working directory,
not the skill installation directory.

Full annotated tree in `references/directory-structure.md`.
