# Troubleshooting

## Skill does not appear after install

Restart Claude Code. New skills are usually detected only at startup.

If you installed via plugin and `/persona` does not resolve, try the namespaced form:

```bash
/claude-persona:persona concept-test Running shoes: 3 concepts
```

## `ModuleNotFoundError: pandas` or chart libraries missing

Install analysis dependencies:

```bash
python3 -m pip install --user -r requirements.txt
```

`report.md` generation is tied to the analysis pipeline, so missing Python
dependencies usually block the full end-to-end flow.

## `failure_stage: "preflight"` in `run_metadata.json`

The backend was not reachable before persona fan-out began.

Check:

- `claude` is installed and authenticated
- the selected backend is available on `PATH`
- the environment allows outbound model calls

## All personas sound too similar

Use the agent-separated path and keep adherence checks enabled:

```bash
python3 scripts/simulate_survey.py \
  --config demo/running-shoes/concept-test/config.json \
  --analyze --report-llm
```

If you bypass the orchestrator or reuse malformed persona files, responses can
collapse toward the same tone.

## Demo commands fail with `file not found`

The running shoes demo config path is:

- `demo/running-shoes/concept-test/config.json`

Older references to `demo/running-shoes/config.json` are stale.

## `report.md` is missing

For existing raw results, regenerate the report with:

```bash
python3 scripts/analyze_results.py \
  --input demo/running-shoes/concept-test/results/results.json \
  --survey-type concept-test \
  --report-only --topic "Running shoes"
```

If there is no `results.json`, you need to run the survey first.

## Tests fail against old demo paths

The bundled tests assume the per-mode demo layout. If you have local branches or
old fixtures, update them to read from `demo/running-shoes/concept-test/results/`
instead of `demo/running-shoes/results/`.
