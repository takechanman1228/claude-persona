# Sampling Plan Prompt

Generate a sampling plan that assigns diversity attributes to each persona
slot. The plan ensures systematic coverage of the population space so that
the LLM generates diverse, non-overlapping personas.

Inspired by TinyTroupe's `TinyPersonFactory._compute_sample_plan()`.

## Instructions

You are a population researcher designing a persona panel for market research.
Given the topic, segments, and exact per-segment counts below, create a
sampling plan: one row per persona, specifying the diversity attributes
that persona should embody.

**Your job is to assign attribute combinations, not to generate personas.**
The personas will be generated in a separate step from this plan.

## Inputs

**Topic**: {{topic}}
**Market**: {{market}}
**Category**: {{category}}

**Segments with allocated counts** (these are FIXED — do not change):
{{segment_allocation}}

**Total personas**: {{count}} (FIXED — your plan must have exactly this many rows)

## Output Format

Return a JSON array with exactly {{count}} objects. Each object is one slot:

```json
[
  {
    "slot": 1,
    "segment": "Segment Name",
    "age_bucket": "20s",
    "gender": "Female",
    "occupation_tier": "professional",
    "geography_type": "urban",
    "region_hint": "Northeast",
    "category_stance": "enthusiastic",
    "ethnicity_hint": "South Asian"
  }
]
```

### Field Definitions

| Field | Values | Purpose |
|-------|--------|---------|
| `slot` | 1 to N | Sequential identifier |
| `segment` | Segment name (from allocation) | Must match exactly |
| `age_bucket` | `"teens"`, `"20s"`, `"30s"`, `"40s"`, `"50s"`, `"60s+"` | Decade range |
| `gender` | `"Male"`, `"Female"`, `"Non-binary"` | Gender identity |
| `occupation_tier` | `"professional"`, `"service"`, `"trade"`, `"creative"`, `"student"`, `"retired"` | Job category (not specific title) |
| `geography_type` | `"urban"`, `"suburban"`, `"small-city"`, `"rural"` | Setting type |
| `region_hint` | US region or equivalent | e.g., "Northeast", "South", "Midwest", "West", "Pacific NW" |
| `category_stance` | `"enthusiastic"`, `"pragmatic"`, `"skeptical"`, `"indifferent"` | Attitude toward the category |
| `ethnicity_hint` | Cultural background hint | e.g., "African-American", "Latino", "East Asian", "White", "South Asian", "Mixed" |

## Constraints (MUST follow)

1. **Exact count**: `len(plan) == {{count}}`. No more, no fewer.
2. **Segment allocation**: Each segment's row count must match the allocation exactly.
3. **Gender balance**: Within each segment, aim for roughly 40-60% split
   between male and female. Include at most 1 non-binary per segment.
4. **Age spread**: Within each segment, distribute across at least 3 different
   age buckets. No age bucket should have more than 40% of the segment's personas.
5. **Geography**: Within each segment, use at least 3 different geography_types
   or region_hints (for segments with 5+ personas).
6. **Occupation diversity**: Vary occupation_tier across personas. No more than
   40% of a segment should share the same occupation_tier.
7. **Category stance**: Include at least 1 "skeptical" or "indifferent" persona
   per segment (for segments with 5+ personas). Not everyone should be enthusiastic.
8. **Ethnicity mix**: Ensure representative diversity — no more than 40% of a
   segment should share the same ethnicity_hint.
9. **No identical rows**: Every row must differ on at least 2 non-slot fields.

## Design Principles

- Think of each row as a **skeleton** that will be fleshed out into a full persona.
  The slot constrains the demographic profile; the LLM adds the personality,
  style, relationships, and life details.
- **Cover the extremes**: Include at least one very young and one older persona,
  at least one budget-conscious and one affluent, at least one skeptic and one
  enthusiast. Avoid a panel of homogeneous moderates.
- **Reflect the market**: If the market is "United States", the ethnicity and
  geography hints should reflect US demographics. For other markets, adapt
  accordingly.
- **Segment coherence**: Personas within the same segment should share the
  segment's core behavioral trait (e.g., all "Serious Runners" actually run
  seriously) while differing on everything else.
