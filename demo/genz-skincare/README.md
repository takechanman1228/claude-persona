# Gen Z Skincare Concept Test — Demo

> Build Panel. Explore Motivations. Run Concept Test.
> 3 skincare concepts. 10 Gen Z personas. Natural language commands.

---

## The Scenario

You are a skincare brand manager preparing to launch a new product line
targeting Gen Z consumers. R&D has three concepts. You want
directional signal from diverse skincare attitudes before committing to
packaging and positioning.

**A: Acne Control Serum** — A targeted treatment serum that fights breakouts
with active ingredients. Designed for acne-prone skin, it uses clinically
proven actives to clear existing blemishes and prevent new ones.

**B: Barrier Repair Cream** — A soothing moisturizer that strengthens your
skin barrier and reduces redness. Formulated for sensitive and stressed skin,
it calms irritation and restores your skin's natural protective layer.

**C: Glow Boosting Toner** — An everyday toner that delivers radiance and
brightens skin tone. A lightweight, daily-use product that evens out
complexion and gives skin a healthy, dewy glow.

---

## 3-Step Workflow

### Step 1: Build Panel

```
/persona generate 10 Gen Z skincare shoppers in the US
```

10 diverse Gen Z personas (ages 18–28 in the generated panel) spanning different skincare attitudes:

| # | Name | Age | Occupation | Segment |
|---|------|-----|------------|---------|
| 1 | Mia Nakamura | 22 | Social Media Coordinator | Routine Devotee |
| 2 | Derek Williams | 27 | Auto Insurance Claims Adjuster | Reluctant Minimalist |
| 3 | Priya Sharma | 24 | Pharmacy Technician | Ingredient Detective |
| 4 | Jordan Rivera | 21 | Barista / Environmental Studies Student | Clean Beauty Advocate |
| 5 | Tyler Kowalski | 19 | Electrical Apprentice | Skincare Skeptic |
| 6 | Aaliyah Jackson | 20 | College Student / Sales Associate | Trend Chaser |
| 7 | Marcus Chen | 28 | Backend Software Developer | Pragmatic Upgrader |
| 8 | Sofia Gutierrez | 26 | Third-Grade Teacher | Budget Beauty Maven |
| 9 | Elijah Foster | 23 | Certified Personal Trainer | Wellness Explorer |
| 10 | Zara Okonkwo | 18 | High School Senior | Anxious Perfectionist |

### Step 2: Explore Motivations

```
/persona ask What frustrates you most about choosing skincare products?
```

Top themes surfaced:
- Ingredient and formula opacity — no concentrations, proprietary blends (5/10)
- Greenwashing and legally meaningless claims ("clean", "clinically proven") (5/10)
- Research burden pushed onto consumers — Reddit, INCIDecoder, PubMed homework (5/10)
- Information and choice overload, producing paralysis or disengagement (5/10)
- Prestige pricing on identical actives, verified by personal comparison (3/10)

### Step 3: Run Concept Test

```
/persona concept-test Compare 3 skincare concepts for Gen Z.

A: Acne Control Serum — fights breakouts with clinically proven actives
B: Barrier Repair Cream — strengthens skin barrier, reduces redness
C: Glow Boosting Toner — everyday radiance, brightens skin tone
```

### Results

> Results generated on `claude-sonnet-4-6` (June 2026; exact model recorded in
> `run_metadata.json`). Close-margin preferences are model-sensitive — see the
> [model sensitivity study](../../docs/MODEL-COMPARISON.md).

- **A: Acne Control Serum** — 4/10 (40%) first choice
- **B: Barrier Repair Cream** — 4/10 (40%) first choice
- **C: Glow Boosting Toner** — 2/10 (20%) first choice
- **Purchase likelihood**: mean 3.2/5, range 1–5

A dead heat — each concept appeals to a distinct attitudinal cluster, and no
single positioning carries this panel. Barrier repair won the
ingredient-conscious and value-driven personas who liked its mechanistic
clarity. Acne control attracted the problem-driven personas — and the
skeptics, who picked the "most functional" option while still doubting it
(purchase likelihood 1–2). Glow toner had the smallest camp but the most
enthusiasm: its two choosers scored 4 and 5, the panel's highest.

[Summary](concept-test/results/summary.json) |
[Results JSON](concept-test/results/results.json) |
[Ask Results](ask/results/results.json)

---



### View pre-generated results (no API calls needed)

Results are already committed. Browse `concept-test/results/` and `ask/results/`.

---

## What's in the Box

```
demo/genz-skincare/
├── README.md                          <- You are here
├── personas/                          <- 10-persona panel
│   ├── manifest.json
│   └── 10 persona JSON files
├── ask/
│   └── results/
│       ├── results.json, report.md, summary.json
│       └── results.csv, persona_comparison.csv
└── concept-test/
    ├── config.json                    <- 3 skincare concepts (A/B/C)
    └── results/
        ├── results.json, report.md, summary.json
        ├── results.csv, persona_comparison.csv
        ├── run_metadata.json
        └── chart_overall.png, chart_purchase_likelihood.png
```

---

## Caveats

- Virtual panel of 10 AI personas; directional only
- Not statistically representative; use for hypothesis generation
- AI-generated responses may exhibit positivity bias
- Panel segments are each represented by a single persona; treat inter-segment splits as directional, not proportional
