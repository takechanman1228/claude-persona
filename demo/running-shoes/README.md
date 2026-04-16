# Running Shoes Concept Test — Demo

> Build Panel. Run Concept Test. Review Findings.
> 3 running shoe concepts. 15 AI personas. Natural language commands.

---

## The Scenario

You are a product manager at a running shoe brand. Engineering has three
concepts ready for consumer testing, but a real panel would take weeks and
cost real budget. You want directional signal today.

**A: Lightweight Comfort** — Minimalist, 7.2 oz, responsive foam, breathable
mesh, flexible outsole. Built for speed and agility.

**B: Soft Cushion Support** — Max cushion, 10.8 oz, dual-density foam, structured
heel counter, reinforced toe box. Built for protection and comfort.

**C: Versatile Style** — Classic silhouette, balanced cushioning, 8 colorways,
track-to-street hybrid. Built for lifestyle and everyday wear.

---

## 3-Step Workflow

### Step 1: Build Panel

```
/persona generate --count 15 Running shoes
```

15 diverse personas generated from the topic "Running shoes" using topic-only mode.
Each persona has a unique archetype, Big Five personality profile, communication
style, and lifestyle details that drive differentiated responses.

| # | Name | Age | Occupation | Archetype |
|---|------|-----|------------|-----------|
| 1 | Jake Morrison | 28 | Sales Account Executive | Marathon Purist |
| 2 | Priya Raghavan | 34 | Pediatrician | Time-Starved Multitasker |
| 3 | Howard Ling | 67 | Retired Civil Engineer | Daily Walker Retiree |
| 4 | DeAndre Fuller | 22 | Graphic Design Student / Barista | Sneaker Culture Collector |
| 5 | Greg Kowalski | 42 | HVAC Service Technician | Reluctant Beginner |
| 6 | Elena Vasquez | 30 | Park Ranger | Trail Adventurer |
| 7 | Diane Caldwell | 45 | PE Teacher & Track Coach | Veteran Coach |
| 8 | Ravi Mehta | 33 | Senior Data Scientist | Data-Driven Optimizer |
| 9 | Jasmine Taylor | 20 | Student / Cross-Country Runner | Budget Racer |
| 10 | Karen Yoshida | 52 | Physical Therapist (DPT) | Injury-Conscious Expert |
| 11 | Zoe Chen | 27 | Social Media Manager | Athleisure Aesthete |
| 12 | Frank Novak | 55 | Auto Body Shop Owner | Category Skeptic |
| 13 | Matt Sorensen | 38 | Wildland Firefighter | Endurance Extremist |
| 14 | Tamara Mitchell | 48 | Assistant Principal | Weekend Warrior Mom |
| 15 | Robert Garcia | 63 | Retired Firefighter | Post-Cardiac Walker |

### Step 2 (Optional): Explore Motivations

```
/persona ask What frustrates you most about buying running shoes online?
```

Run this before the concept test to discover the language and pain points that
should shape your concept descriptions. Each persona answers independently.

### Step 3: Run Concept Test

```
/persona concept-test Compare 3 running shoe concepts.

A: Lightweight Comfort — Minimalist, 7.2 oz, responsive foam, breathable mesh. Built for speed.
B: Soft Cushion Support — Max cushion, 10.8 oz, dual-density foam, structured heel counter. Built for protection.
C: Versatile Style — Classic silhouette, balanced cushioning, 8 colorways, hybrid design. Built for lifestyle.
```

Each persona responds independently in its own `claude -p` subprocess — zero
cross-contamination between personas.

### Step 4: Review Findings

- **Distribution**: A 6 (40%), B 6 (40%), C 3 (20%)
- **Purchase likelihood**: mean 3.1/5, median 3.0/5 — no persona scored 5
- A and B tie at 6 each — but for entirely different reasons (performance vs. medical/comfort)
- The physical therapist (Karen Yoshida) chose A over B — citing clinical concern about max-cushion platforms weakening foot intrinsics
- Concept C has the smallest volume but highest enthusiasm: all 3 choosers scored 4/5
- Specs opacity (missing drop, stack height, energy return %) is the #1 barrier across all concepts
- Wide-width availability was flagged by 3 of 15 personas as a deal-breaker

[Summary](concept-test/results/summary.json) |
[Results JSON](concept-test/results/results.json) |
[Charts](concept-test/results/)

---


### View pre-generated results (no API calls needed)

Results are already committed. Open `concept-test/results/report.md` to read findings.

---

## What's in the Box

```
demo/running-shoes/
├── README.md                          <- You are here
├── personas/                          <- 15-persona panel
│   ├── manifest.json
│   └── 15 persona JSON files
└── concept-test/
    ├── config.json                    <- 3 shoe concepts (A/B/C)
    └── results/
        ├── results.json, report.md, summary.json
        ├── results.csv, persona_comparison.csv
        ├── run_metadata.json
        └── chart_overall.png, chart_purchase_likelihood.png
```

---

## Caveats

- Virtual panel of 15 AI personas; directional only
- Not statistically representative; use for hypothesis generation
- AI-generated responses may exhibit positivity bias
- Panel segments are each represented by a single persona; treat inter-segment splits as directional, not proportional
