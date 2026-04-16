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
- Hidden ingredient concentrations and unverifiable efficacy claims
- Greenwashing disguised as clean beauty
- Too many choices, too much marketing noise
- TikTok hype vs. real results
- Overpriced basics with a prestige tax on identical ingredients

### Step 3: Run Concept Test

```
/persona concept-test Compare 3 skincare concepts for Gen Z.

A: Acne Control Serum — fights breakouts with clinically proven actives
B: Barrier Repair Cream — strengthens skin barrier, reduces redness
C: Glow Boosting Toner — everyday radiance, brightens skin tone
```

### Results

- **B: Barrier Repair Cream** — 4/10 (40%) first choice
- **A: Acne Control Serum** — 3/10 (30%) first choice
- **C: Glow Boosting Toner** — 3/10 (30%) first choice
- **Purchase likelihood**: mean 3.3/5, range 2–5

No clear majority — each concept appeals to a distinct attitudinal cluster.
Barrier repair won among ingredient-conscious personas who valued its
mechanistic clarity. Glow toner pulled the routine-devoted and trend-chasing
personas drawn to its aesthetic appeal. Acne control attracted problem-driven
and skeptical personas who wanted something that "actually does something."

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
