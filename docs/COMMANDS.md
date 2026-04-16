# Commands

`claude-persona` exposes two user-facing commands, matching the
three-step workflow: Build Panel, Run Concept Test, Review Findings.

## Command Matrix

| Command | Use it when you need to decide... | Typical input | Returns | Demo |
|---------|-----------------------------------|---------------|---------|------|
| `/persona concept-test` | which concept, message, design, or bundle wins | 2-4 option descriptions | `results.json`, `summary.json`, `report.md` | [`running-shoes/concept-test`](../demo/running-shoes/concept-test/README.md) |
| `/persona generate` | who to talk to before running studies | topic and optional count | persona JSON files + manifest | n/a |

## Examples

```bash
# Product concept comparison
/persona concept-test Running shoes: 3 concepts to evaluate

# Message A/B test
/persona concept-test Compare 2 ad headlines for our new energy drink

# Package design evaluation
/persona concept-test Which package design resonates with parents?

# Build a reusable panel
/persona generate --count 15 Running shoes
```

Concept test covers any comparison research: product concepts, messaging A/B,
packaging, competitive comparisons, feature bundles, and value framing with
price context.

## Options

| Option | Meaning | Default |
|--------|---------|---------|
| `--count N` | panel size | `5` |
| `--market MARKET` | target market/country (codes like `us`, `japan`, `uk` or freeform) | `us` |
| `--segments` | use segment-driven generation flow | off |
| free text | topic, concepts, or comparison items | asked only if missing |

## Output Contract

Every full run is expected to produce:

- `results.json`: canonical persona responses
- `run_metadata.json`: backend, latency, adherence, and failure-stage metadata
- `summary.json`: aggregated metrics for the study
- `report.md`: executive narrative report
- `results.csv` and optional charts when analysis is enabled

For deeper argument and input details, see `references/command-details.md`.
