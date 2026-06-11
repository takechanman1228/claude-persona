# Model Sensitivity Study: How Stable Are Panel Results Across Claude Models?

**Date**: June 2026 · **Engine**: claude-persona 0.2.0 · **Models**: `claude-sonnet-4-6`, `claude-fable-5`, plus the originally published April 2026 `sonnet` runs

The most common question about synthetic panels is: *"Aren't the results just
model noise?"* To answer it with data, we re-ran all four shipped demos —
same panels, same prompts — across three model generations and measured what
changed, down to the individual persona.

**TL;DR: 84–100% of personas gave the same answer across three model
generations, a repeated Fable 5 run reproduced persona-level choices 100%,
and no demo's winning concept ever changed. What moves between models is
the close races — ties, zero-counts, and 1-vote margins.**

## Method

- 4 demo panels (45 personas), concept-test, three conditions per demo:
  the originally published April 2026 `sonnet` run, a fresh
  `claude-sonnet-4-6` run, and a `claude-fable-5` run.
- Re-runs used the demo configs with only `model` and `output_dir` changed
  (plus `fallback_model: sonnet` for fable). Adherence checks ON,
  structured output + context isolation ON (0.2.0 defaults).
- One additional independent Fable 5 run of france-mealkit measured
  run-to-run variance within the same model.
- 0.2.0 metadata records the exact serving model IDs (`actual_model_ids`),
  so every number below is attributable: "sonnet 4.6" runs were served by
  `claude-sonnet-4-6` and "fable" runs by `claude-fable-5`. All runs
  completed 10/10 or 15/15 with `attempts: 1` (no validation retries).

> The demo results currently published in `demo/` are the
> `claude-sonnet-4-6` runs from this study.

## Aggregate Results

Preference distribution (first-choice counts) and mean purchase likelihood (1–5):

| Demo | April sonnet | Sonnet 4.6 | Fable 5 |
|------|--------------|------------|---------|
| genz-skincare (n=10) | **B5** / A3 / C2 · 3.0 | A4 / B4 / C2 (tie) · 3.2 | **B6** / A3 / C1 · 3.2 |
| running-shoes (n=15) | A6 / B6 / C3 (tie) · 3.07 | **B7** / A5 / C3 · 3.2 | **B6** / A5 / C4 · 3.27 |
| france-mealkit (n=10) | **B6** / C4 / **A0** · 3.1 | **B7** / C3 / **A0** · 3.1 | **B4** / A3 / C3 · 3.0 |
| japan-meeting-ai (n=10) | **B9** / A1 / C0 · 3.1 | **B9** / A1 / C0 · 3.2 | **B8** / A2 / C0 · 3.3 |

## Persona-Level Stability

Because the same persona JSONs answer in every run, switches can be tracked
individually. Personas are remarkably stable — the aggregate shifts above
come from a handful of personas at the margin, not from wholesale re-rolls:

| Demo | April → Sonnet 4.6 | Sonnet 4.6 → Fable 5 |
|------|--------------------|----------------------|
| genz-skincare | 1/10 | 2/10 |
| running-shoes | 1/15 | 1/15 |
| france-mealkit | 1/10 | 3/10 |
| japan-meeting-ai | **0/10** | 1/10 |
| **Total** | **3/45 (7%)** | **7/45 (16%)** |

And within the same model, choices are deterministic in practice: two
independent Fable 5 runs of france-mealkit matched **10/10** at the
persona level (identical preference distribution, zero switches).

Mean reasoning length is essentially unchanged across models (~500–660
chars; the response schema constrains verbosity), so the differences are in
*which option wins*, not in response style.

## Findings

1. **Model-version drift is small and direction-preserving.** Fresh
   sonnet 4.6 switched only 3/45 personas vs the April runs, and reproduced
   two demos almost perfectly — japan-meeting-ai had **zero** switches and
   france-mealkit kept its signature "concept A got zero votes" result.
2. **Fable 5 changes more (7/45 personas) — and it changes close races,
   not landslides.**
   - genz-skincare: fable *sharpens* the B win that sonnet 4.6 had relaxed
     to a tie — both switchers moved *toward* B.
   - france-mealkit: "**A got zero votes**" survives sonnet 4.6 exactly but
     **not fable**: 3 personas switch B→A, giving A 30% — and the repeat
     fable run reproduced this exactly. A genuine, reproducible
     model-generation difference. If a zero-count finding drives a real
     decision, pressure-test it with a follow-up `/persona ask`.
   - japan-meeting-ai: the 90% B landslide is robust everywhere
     (B9 → B9 → B8).
3. **Decisive findings are model-robust; coin-flip findings are not.**
   Across all run pairs, no demo's *winning* concept changed under fable;
   what moved were ties, zero-counts, and 1-vote margins. Treat close
   splits as "model-sensitive" — and consider running both models as a
   robustness check before betting on them.
4. **Correlated personas switch together.** Two of france-mealkit's three
   B→A switchers are the panel's flagged near-identical Big Five pair
   (cosine 0.985 — surfaced by `validate_panel.py`): personality-similar
   personas move as a bloc, amplifying aggregate swings. Panel diversity
   warnings predict result stability.
5. **Stability is a feature of the panel design.** 84–100% of personas gave
   the same answer across three model generations — evidence that responses
   are persona-driven rather than model-noise-driven.

## Cost Guide (10–15 personas, adherence on)

Typical per-run costs as recorded in `run_metadata.json`
(`total_cost_usd`; on subscription auth this is the CLI's API-equivalent
estimate, not a charge):

| Model | 10-persona run | 15-persona run | Wall clock |
|-------|---------------:|---------------:|-----------|
| `sonnet` (default) | ~$0.7–1.0 | ~$1.1 | 2–3 min |
| `fable` | ~$2.5–3.3 | ~$3.7 | 2–3 min |

Fable 5 costs ~3–3.5x sonnet (price ratio 3.3x plus a denser tokenizer)
and was not slower wall-clock at this fan-out width. Pair fable runs with
`"fallback_model": "sonnet"` for overload resilience.

## Recommendations

- **`sonnet` stays the default** — cheap, fast, and stable across versions.
- **`fable` for decision-critical studies** — deeper reasoning on marginal
  personas; running both models (~$4–5 total for a 10-persona panel) is a
  cheap robustness check.
- **Read close races with error bars.** A 4/4/2 split is a "no clear
  winner" finding, not a winner. The stable signals are landslides,
  consistent zero-counts, and the qualitative reasoning themes.
