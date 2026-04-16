# Topic-Only Persona Generation Flow

This is the default flow when `--segments` is not specified. It mirrors TinyPersonFactory's
`_compute_sampling_dimensions()` + `_compute_sample_plan()` approach as inline Claude reasoning.

## Step 1: Diversity Dimension Inference (Claude internal reasoning)

Determine 3-5 diversity axes relevant to the topic **and the target market**. These are
**independent dimensions**, not predefined clusters (segments). Each dimension has a range
of possible values. Consider market-specific diversity factors (e.g., for Japan: urban vs
regional, traditional vs modern lifestyle; for US: coastal vs heartland, urban vs rural).

Example for "canned coffee":
| Dimension | Low end | High end |
|-----------|---------|----------|
| Usage frequency | Non-user / rare | Daily heavy user |
| Health consciousness | Doesn't think about it | Actively health-focused |
| Price sensitivity | Price-insensitive | Very budget-conscious |
| Age / life stage | Student / young adult | Middle-aged / retired |
| Category attitude | Skeptical / prefers fresh brew | Enthusiastic / loyal |

## Step 2: Diversity Target Assignment (per persona)

For N personas, assign each persona a target position across all dimensions
to maximize spread:

- **N = 5** (default): Cover extreme positions on each major dimension
- **N = 3**: Each persona should differ on at least 2-3 dimensions
- **N ≤ 5**: Apply Small Panel Diversity Rules (see generation prompt)
- **Goal**: No two personas should be "neighbors" in the dimension space

Example for N = 5 (canned coffee):
| Persona | Usage | Health | Price | Attitude |
|---------|-------|--------|-------|----------|
| P1 | Heavy daily | Low | Low sensitivity | Enthusiastic loyalist |
| P2 | Rare / non-user | High | High sensitivity | Skeptical rejecter |
| P3 | Moderate | Medium | Medium | Pragmatic switcher |
| P4 | Heavy daily | High | Low sensitivity | Health-conscious upgrader |
| P5 | Light occasional | Low | High sensitivity | Budget convenience seeker |

## Step 3: Persona Generation

Use `references/persona-generation-prompt-topiconly.md` with:
- `{{topic}}` = the research topic
- `{{market}}` = the target market (default: "United States")
- `{{diversity_dimensions}}` = the dimensions and target positions from Step 2
- `{{count}}` = N (default: 5)

Generate all N personas in a single batch. Each persona receives a unique
**archetype label** in the `segment` field (e.g., "Budget Pragmatist", "Health Explorer").

## Step 4: manifest.json Creation

Create `personas/{survey-id}/manifest.json`:
```json
{
  "survey_id": "canned-coffee-2026-03",
  "topic": "Canned coffee product concepts",
  "category": "Canned Coffee / RTD Beverages",
  "market": "United States",
  "generation_mode": "topic-only",
  "diversity_dimensions": [
    "usage_frequency",
    "health_consciousness",
    "price_sensitivity",
    "category_attitude"
  ],
  "total_personas": 5,
  "created": "2026-03-16",
  "persona_files": ["Marcus_Chen.json", "Diana_Okafor.json", "Jake_Morales.json", "Sofia_Rivera.json", "Tom_Nguyen.json"]
}
```

## Difference from Segment-Driven Flow

| Aspect | Topic-only | Segment-driven |
|--------|-----------|----------------|
| User input | Topic only | Topic + segment approval |
| Grouping | Per-persona archetype labels | Shared segment names |
| Default N | 5 | 15 (3 segments × 5) |
| Diversity method | Independent dimension axes | Within-segment variation |
| Confirmation | Panel table only | Segment table → panel table |
| manifest.json | `"generation_mode": "topic-only"` | `"generation_mode": "segment-driven"` |
| Cross-tab analysis | Persona comparison table | Segment × response table |
