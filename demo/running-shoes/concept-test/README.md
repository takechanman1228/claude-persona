# Running Shoes Concept Test

This is the strongest bundled demo in the repository: three shoe concepts, a
15-persona panel, pre-generated structured outputs, and a narrative report.

## Run

```
/persona concept-test Compare 3 running shoe concepts
```

Or via script:

```bash
python scripts/simulate_survey.py \
  --config demo/running-shoes/concept-test/config.json \
  --analyze --report-llm
```

## Snapshot

- A and B tied at 6 each (40%); C trailed at 3 (20%)
- Mean purchase likelihood: `3.1 / 5`
- The physical therapist chose A over B — clinical concern about max-cushion weakening foot intrinsics
- Specs opacity (drop, stack height, energy return %) is the #1 barrier across all concepts
- Concept C has the highest enthusiasm among its choosers (all scored 4/5)

## Open

- `results/report.md`
- `results/summary.json`
- `results/chart_overall.png`
- `results/chart_purchase_likelihood.png`
