# Persona JSON Schema

This document defines the JSON schema for personas used in Persona Research virtual surveys.
The schema is based on the `TinyPerson` format from the PyData demo,
ensuring compatibility with existing persona libraries.

## Schema

```json
{
  "persona": {
    "name": "string (required) — Full name",
    "age": "integer (required) — Age in years",
    "nationality": "string (required) — e.g. 'American', 'Japanese-American'",
    "occupation": {
      "title": "string (required) — Job title",
      "organization": "string (required) — Employer or context",
      "description": "string (required) — What they do day-to-day (2-4 sentences)"
    },
    "gender": "string (required) — e.g. 'Male', 'Female', 'Non-binary'",
    "residence": "string (required) — City, Region (US: 'City, State'; Japan: 'City, Prefecture'; UK: 'City, Country')",
    "education": "string (required) — Narrative description of educational background",
    "long_term_goals": ["string — 3-5 life goals"],
    "style": "string (required) — Communication style, appearance, mannerisms (3-5 sentences). THIS FIELD DRIVES RESPONSE TONE.",
    "personality": {
      "traits": ["string — 5-8 personality descriptions"],
      "big_five": {
        "openness": "float 0.0-1.0",
        "conscientiousness": "float 0.0-1.0",
        "extraversion": "float 0.0-1.0",
        "agreeableness": "float 0.0-1.0",
        "neuroticism": "float 0.0-1.0"
      }
    },
    "preferences": {
      "interests": ["string — 5-10 interests"],
      "likes": ["string — 5-10 things they enjoy"],
      "dislikes": ["string — 5-10 things they avoid"]
    },
    "beliefs": ["string — 3-5 core beliefs or values"],
    "skills": ["string — 3-5 relevant skills"],
    "behaviors": {
      "general": ["string — 3-5 typical behaviors"],
      "routines": {
        "morning": ["string"],
        "workday": ["string"],
        "evening": ["string"],
        "weekend": ["string"]
      }
    },
    "health": {
      "physical": "string — Physical health summary",
      "mental": "string — Mental health summary"
    },
    "relationships": [
      {
        "name": "string",
        "relation": "string",
        "description": "string"
      }
    ]
  },
  "segment": "string (required) — Generic segment label for analysis (e.g. 'Daily Ritual Drinker', 'Early Adopter')",
  "segment_id": "integer (required) — Numeric segment identifier (1-based, matches segment order)"
}
```

## Generation Guidelines

### What Makes a Good Persona for Virtual Surveys

1. **Big Five personality** is the primary driver of response variation:
   - High openness → exploratory, willing to try new things
   - High conscientiousness → detail-oriented, researches before buying
   - High extraversion → enthusiastic, verbose responses
   - High agreeableness → positive bias, avoids criticism
   - High neuroticism → anxious about purchases, risk-averse

2. **Style field** controls expression quality:
   - A laconic farmer writes differently than a verbose marketing exec
   - Education level should match vocabulary complexity
   - Cultural background influences communication patterns

3. **Income/occupation** drives price sensitivity:
   - Don't state income directly — imply through occupation and lifestyle
   - A nurse and a hedge fund manager react differently to $300 shoes

4. **Diversity requirements** (per panel of 15+):
   - Age range: at least 3 decades represented (e.g., 20s, 40s, 60s+)
   - Gender: mixed
   - Income: budget-conscious to affluent
   - Geography: urban, suburban, rural
   - Ethnicity: representative mix
   - Personality: mix of Big Five profiles (not all agreeable/open)

### Minimal vs Full Persona

**Minimal** (for quick surveys, ≤10 personas):
- name, age, occupation.title, gender, residence, style
- personality.big_five (numeric scores)
- 2-3 key preferences/interests relevant to the survey topic

**Full** (for rich simulations, reusable library):
- All fields populated as in the schema above
- Detailed style, behaviors, and routines
- 10+ interests, likes, dislikes each

### Segment-Driven Generation

When generating personas from segment definitions:

```json
{
  "segments": [
    {
      "name": "Serious Runner",
      "count": 10,
      "description": "Runs 30+ miles/week, values performance...",
      "demographic_priors": {
        "age_range": [25, 55],
        "income_signal": "moderate to high",
        "fitness_level": "high"
      }
    }
  ]
}
```

Each persona within a segment should vary — they share the segment's core trait
but differ in age, personality, background, and priorities.

### Segment Field Convention

The `segment` field is used for all analysis (cross-tabs, charts, comparisons).
Its meaning depends on the generation mode:

**Segment-driven mode** (`--segments`): Shared segment label for grouping.
Multiple personas share the same segment name.
- **Good**: "Daily Ritual Drinker", "Early Adopter", "Budget-Conscious Parent"
- **Avoid**: "Segment A", "Group 1" (not descriptive)

**Topic-only mode** (default): Per-persona archetype label — each persona gets a
unique 2-4 word label describing their relationship to the topic.
- **Good**: "Budget Pragmatist", "Health-Focused Explorer", "Skeptical Minimalist"
- **Avoid**: Generic labels that don't convey persona character
- **Format**: Adjective + Noun pattern preferred
- When unique labels are used, analysis produces persona comparison tables
  instead of segment cross-tabulations.

**Deprecated**: Topic-specific field names like `runner_type`, `coffee_preference`, etc.
should NOT be used. All segment grouping must go through the standard `segment` field.
Legacy personas with `runner_type` or similar fields remain valid but the `segment` field
takes precedence for analysis.

### Persona Storage

Personas are stored in per-survey subdirectories:

```
personas/
├── _archive/                  # Archived panels (ignored by auto-detection)
│   └── shoes-demo-2025/       # Legacy shoe demo personas
├── {survey-id}/               # Active panels
│   ├── manifest.json          # topic, category, segments, count, created
│   └── {Name_Underscored}.json
```

Each `manifest.json` identifies the panel's topic and segments, enabling
automatic reuse detection across surveys.
