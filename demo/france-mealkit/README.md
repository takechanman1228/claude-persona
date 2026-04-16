# France Meal Kit Concept Test — Demo

> Customer-data-driven panel. Non-US market. 3 acquisition concepts.
> 10 AI personas in France. Natural language commands.

---

## The Scenario

You are a meal kit company expanding into France. You have existing customer
data showing your subscriber mix. Before investing in acquisition creative,
you want directional signal on which positioning resonates with first-time
subscribers.

**Your customer data:**
- 38% are dual-income couples without children
- 27% are families with children under 12
- High-value customers skew Paris, Lyon, and Nantes

**A: Easy First Step** — Simple and low pressure for first-time users, with
straightforward meals and an easy way to skip or cancel.

**B: Risk Reduction** — Focused on reducing the fear of wasting money,
choosing the wrong meals, or getting stuck in a subscription that does not fit.

**C: Better Weeknights Fast** — Promises to make weeknight dinners feel
noticeably easier and more enjoyable within the first week.

---

## What Makes This Demo Different

1. **Customer data in the generate command** — Instead of just describing
   the target audience, you feed your actual customer segment mix (38% DINK,
   27% families, geo skew) into the prompt. The generated panel reflects
   your real customer base proportions.

2. **Non-US market** — Setting the market to France produces personas with
   French names, French cities, local cultural references (Marche d'Aligre,
   Halles Paul Bocuse, Talensac market), and some responses in native French.

---

## 3-Step Workflow

### Step 1: Build Panel

```
/persona generate 10 first time potential meal kit subscribers in France, based on these existing customer patterns:

1. 38 percent are dual income couples without children
2. 27 percent are families with children under 12
3. High value customers skew Paris, Lyon, and Nantes
```

10 personas generated across 3 customer-data-driven segments:

| # | Name | Age | Occupation | Segment |
|---|------|-----|------------|---------|
| 1 | Camille Renaud | 34 | Senior UX Designer | Dual-Income Couples Without Children |
| 2 | Yassine Benali | 28 | Motion Graphics Designer | Dual-Income Couples Without Children |
| 3 | Nathalie Guerin | 42 | Regional HR Director | Dual-Income Couples Without Children |
| 4 | Remi Edouard | 36 | Independent Electrician | Dual-Income Couples Without Children |
| 5 | Mei-Lin Gerard | 33 | Pediatric Nurse | Families With Young Children |
| 6 | Christophe Morel | 44 | Insurance Claims Adjuster | Families With Young Children |
| 7 | Amadou Diallo | 35 | IT Project Manager | Families With Young Children |
| 8 | Priya Sharma | 26 | Doctoral Researcher | Independent Professionals & Empty Nesters |
| 9 | Florian Roche | 38 | Freelance Web Developer | Independent Professionals & Empty Nesters |
| 10 | Katarina Novak | 54 | Deputy School Principal | Independent Professionals & Empty Nesters |

The panel reflects France's demographic diversity: North African French,
East Asian French, West African French, Eastern European French, and South
Asian French personas alongside White French personas — across Paris,
Lyon, Nantes, Bordeaux, Toulouse, and Strasbourg.

### Step 2: Explore Motivations

```
/persona ask What would make you finally try a meal kit subscription for the first time, and what still holds you back?
```

Top themes surfaced:
- Subscription lock-in distrust — auto-renewal traps, opaque cancellation
- Local market ritual competes — Marche d'Aligre, Halles Paul Bocuse, Talensac
- Ingredient provenance demands — "which farm, not just 'French farms'"
- Portions mismatch — too small for manual workers, too large for solo living
- Cultural recipe invisibility — menus assume Mediterranean, ignore West African, South Asian cuisines
- Food waste anxiety — shift workers fear ingredients going bad

### Step 3: Run Concept Test

```
/persona concept-test

Concept A: Easy First Step
A meal kit subscription designed to feel simple and low pressure for first time users, with straightforward meals and an easy way to skip or cancel.

Concept B: Risk Reduction
A dinner kit offer focused on reducing the fear of wasting money, choosing the wrong meals, or getting stuck in a subscription that does not fit.

Concept C: Better Weeknights Fast
A meal service that promises to make weeknight dinners feel noticeably easier and more enjoyable within the first week of trying it.
```

### Results

- **B: Risk Reduction** — 6/10 (60%) first choice
- **C: Better Weeknights Fast** — 4/10 (40%) first choice
- **A: Easy First Step** — 0/10 (0%) first choice
- **Purchase likelihood**: mean 3.1/5, range 2–4

Concept A received zero votes. Nobody in France needed to be told meal kits
are "simple" — they already know how to cook. The real barriers are structural:
subscription traps, wasted money, and cultural fit.

**Segment split reveals a clear pattern:**

| Segment | B (Risk Reduction) | C (Better Weeknights) |
|---------|-------------------|-----------------------|
| Dual-Income Couples (4) | 1 | 3 |
| Families With Children (3) | 2 | 1 |
| Independent Professionals (3) | 3 | 0 |

- **DINKs prefer C** (3/4) — time-pressed but confident cooks who want a concrete weeknight improvement
- **Families split** — risk concerns (cost, kid-friendliness) compete with time pressure
- **Independents unanimously chose B** (3/3) — budget-conscious, subscription-wary, need risk removed first

**Notable**: Two personas (Remi, Yassine) responded entirely in French — a
natural behavior when the market is set to France.

[Summary](concept-test/results/summary.json) |
[Results JSON](concept-test/results/results.json) |
[Ask Results](ask/results/results.json)

---

### View pre-generated results (no API calls needed)

Results are already committed. Browse `concept-test/results/` and `ask/results/`.

---

## What's in the Box

```
demo/france-mealkit/
├── README.md                          <- You are here
├── personas/                          <- 10-persona panel (France)
│   ├── manifest.json
│   └── 10 persona JSON files
├── ask/
│   └── results/
│       ├── results.json, report.md, summary.json
│       └── results.csv, run_metadata.json
└── concept-test/
    ├── config.json                    <- 3 meal kit concepts (A/B/C)
    └── results/
        ├── results.json, report.md, summary.json
        ├── results.csv, cross_tabs.csv, cross_tabs_pct.csv
        ├── run_metadata.json
        └── chart_overall.png, chart_purchase_likelihood.png, chart_preference.png
```

---

## Caveats

- Virtual panel of 10 AI personas; directional only
- Not statistically representative; use for hypothesis generation
- AI-generated responses may exhibit positivity bias
- Panel segments are each represented by a small number of personas; treat inter-segment splits as directional, not proportional
