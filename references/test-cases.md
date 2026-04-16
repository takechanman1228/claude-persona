# Trigger & Functional Test Cases

## 0. Deterministic Smoke Checks

Run these from the `claude-persona/` directory on normal code changes.

### Unit tests

```bash
python3 -m unittest discover -s tests -v
```

### Syntax / import smoke

```bash
python3 -m py_compile scripts/*.py
```

### Analyze-only smoke on a temp copy

This avoids overwriting tracked demo outputs while still testing the analysis path.

```bash
tmpdir="$(mktemp -d)"
cp demo/running-shoes/concept-test/results/results.json "$tmpdir/results.json"
python3 scripts/analyze_results.py \
  --input "$tmpdir/results.json" \
  --survey-type concept-test \
  --report-only
```

### Large-change dry run

Use this after prompt, config, or orchestration edits.

```bash
python3 scripts/simulate_survey.py \
  --config demo/running-shoes/concept-test/config.json \
  --dry-run
```

### Ask dry run

```bash
python3 scripts/simulate_survey.py \
  --config configs/running-shoes-ask-demo.json \
  --dry-run
```

## 1. Triggering Tests

### Should trigger (skill loads)

```
- "Run a concept test for 3 new canned coffee products"
- "Evaluate new canned coffee products"
- "I want to do virtual consumer research on running shoes"
- "Help me test these 3 product concepts with virtual consumers"
- "Compare two ad headlines with a persona panel"
- "Which package design resonates best with parents?"
- "Generate a persona panel for EV purchase research"
- "/persona concept-test EV concepts"
- "I need a market research simulation for new snack brands"
- "Run a virtual consumer panel study"
- "Run a concept test with a 5-persona panel"
- "/persona ask What frustrates you most about buying running shoes online?"
- "/persona ask Why would you ignore this skincare ad?"
- "Ask my panel what they think about this pricing"
- "Ask the running shoes panel what they think about this new design"
- "I want to explore motivations before doing a concept test"
```

### Should NOT trigger (skill stays inactive)

```
- "Help me write Python code"
- "What's the weather in San Francisco?"
- "Create a presentation about our product"
- "Analyze this CSV file"
- "Help me create a TinyPerson persona" (different TinyTroupe framework)
- "Generate a marketing persona document" (not survey-based research)
- "Review this pull request"
- "Write unit tests for my code"
```

Note: Claude may skip invoking the skill for very simple, single-step requests
even when the description matches. Test with realistic multi-step requests
(e.g., "run a concept test with 5 personas for 3 soda concepts" rather than
just "concept test").

## 2. Functional Tests

### Ask (end-to-end)

```
Test: /persona ask What frustrates you most about buying running shoes online?
Given: personas/running-footwear-us-15p-2026-04 panel exists
When: Skill completes ask workflow
Then:
  - Panel auto-detected (no --panel flag needed)
  - simulate_survey.py runs with survey_type=ask
  - results.json has N entries, each with short_answer and reasoning in responses
  - summary.json has top_signals, emotion_distribution
  - report.md includes Theme Analysis, Response Profiles, Notable Verbatims
  - No preflight or validation failures
```

### Ask (dry-run, no API call)

```bash
python3 scripts/simulate_survey.py \
  --config configs/running-shoes-ask-demo.json \
  --dry-run
```

Success: Prints first persona's prompt containing the user_question. Exits 0.

### Concept test (end-to-end)

```
Test: /persona concept-test Evaluate 3 new canned coffee concepts
Given: 3 concept descriptions provided interactively
When: Skill completes full workflow
Then:
  - 5 personas generated with unique archetype labels
  - manifest.json created in personas/{survey-id}/
  - simulate_survey.py runs with --backend claude-cli
  - results.json has 5 entries with valid responses
  - report.md generated with Key Findings, Profile Analysis, Verbatims
  - No preflight or validation failures
```

### Message A/B test

```
Test: /persona concept-test Compare 2 ad headlines for our new energy drink
Given: 2 headline options provided
When: Skill completes full workflow
Then:
  - 5 personas generated with relevant diversity for energy drink consumers
  - results.json has 5 entries with preferred_option and reasoning
  - report.md identifies which headline resonates and with which personas
```

## 3. Performance Comparison

### Without skill
- User provides instructions each time
- 10-15 back-and-forth messages to set up personas + survey
- Inconsistent output format across sessions

### With skill
- Automatic workflow execution from single command
- 2-3 clarifying questions only (missing concept details)
- Consistent results.json + report.md format every time
- Reproducible persona generation via manifest.json

## 4. Release Gate Controlled E2E

Do not run this on every small change. Use it before release or after major workflow changes.

```bash
python3 scripts/simulate_survey.py \
  --config demo/running-shoes/concept-test/config.json \
  --analyze --report-llm
```

Success criteria:

- backend preflight succeeds
- `failure_stage` remains `null`
- `results.json`, `run_metadata.json`, `summary.json`, and `report.md` are generated
- no unexpected `validation_issues` remain in `per_persona`
