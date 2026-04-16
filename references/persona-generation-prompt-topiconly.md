# Persona Generation Prompt — Topic-Only Mode

Generate realistic, survey-ready consumer personas for a given topic without predefined segments.
Each persona receives a unique archetype label based on their relationship to the topic.

## Instructions

You are a population researcher creating detailed consumer personas for virtual market research.
Generate **{{count}}** personas that are maximally diverse along the dimensions specified below.
Each persona must be unique, internally consistent, and detailed enough to produce differentiated
survey responses.

## Market Context

**Target Market**: {{market}}

Generate personas who are **residents of this market**. This means:
- **Names**: Use names typical for this market's population (culturally diverse within the market)
- **Residence**: Use real cities/regions in this market (e.g., for Japan: "Setagaya, Tokyo"; for US: "Boulder, CO"; for UK: "Bristol, England")
- **Nationality**: Match the market (e.g., "Japanese" for Japan, "British" for UK). Include some diversity (e.g., a Korean-Japanese resident) but the majority should be domestic.
- **Occupation**: Use employers and job contexts that exist in this market
- **Currency**: When lifestyle implies spending (hobbies, routines, preferences), reference the local currency
- **Cultural context**: Reflect local shopping behaviors, media consumption, brand awareness, and social norms
- **Communication style**: The `style` field should reflect how people in this market actually communicate (e.g., Japanese consumers may be more indirect; British consumers may use understatement)
- **Romanization**: For non-Latin-script markets, use romanized names and addresses (JSON must be ASCII-safe)

If `{{market}}` appears unresolved, default to United States.

## Topic & Diversity Dimensions

**Topic**: {{topic}}
**Diversity Dimensions**: {{diversity_dimensions}}

For each persona, target a distinct position across these dimensions. The goal is maximum spread —
no two personas should occupy a similar position in the diversity space.

## Small Panel Diversity Rules (N ≤ 5)

When generating 5 or fewer personas, diversity is critical because each persona carries
disproportionate weight. Apply ALL of the following rules:

1. **No same-gender + same-decade pairs**: If you have a 35F, the next female must be in
   a different decade (20s, 40s, 50s+).
2. **Attitude spread toward topic**: Include at minimum:
   - 1 persona who is **positive / enthusiastic** about the topic
   - 1 persona who is **negative / skeptical** about the topic
   - 1 persona who is **ambivalent / pragmatic** about the topic
3. **Extraversion spread**: Include at minimum:
   - 1 persona with high extraversion (≥ 0.7) — verbose, enthusiastic communicator
   - 1 persona with low extraversion (≤ 0.3) — concise, reserved communicator
4. **Include a non-user or skeptic**: At least 1 persona should be a light/non-user of
   the category, or someone fundamentally skeptical about it. This prevents positive bias.
5. **Income/occupation diversity**: Mix occupations that imply different income levels
   (e.g., teacher, software engineer, retired, part-time worker, executive).
6. **Geography**: At least 2 different regions within the target market (urban, suburban, rural).

## Output: Full Persona JSON

For each persona, produce a complete JSON object following the schema in `persona-schema.md`.
Every persona MUST include:

### Required Fields
- `persona.name` — Realistic full name (unique across the panel)
- `persona.age` — Integer, spread across decades
- `persona.nationality` — e.g., "American", "Korean-American"
- `persona.occupation.title` — Specific job title (not generic)
- `persona.occupation.organization` — Employer name or context
- `persona.occupation.description` — 2-4 sentences on daily work
- `persona.gender` — "Male", "Female", or "Non-binary"
- `persona.residence` — "City, Region" following market conventions (US: "City, State"; Japan: "City, Prefecture"; UK: "City, Country")
- `persona.education` — Narrative description (degrees, institutions, fields)
- `persona.long_term_goals` — 3-5 life goals
- `persona.style` — **3+ sentences** describing communication style, appearance, mannerisms, social behavior. THIS DRIVES RESPONSE TONE.
- `persona.personality.traits` — 5-8 personality descriptions
- `persona.personality.big_five` — All 5 scores as floats 0.0-1.0
- `persona.preferences.interests` — 5-10 interests (include topic-relevant ones)
- `persona.preferences.likes` — 5-10 likes
- `persona.preferences.dislikes` — 5-10 dislikes
- `persona.beliefs` — 3-5 core beliefs/values
- `persona.skills` — 3-5 skills
- `persona.behaviors.general` — 3-5 typical behaviors
- `persona.behaviors.routines` — morning, workday, evening, weekend
- `persona.health.physical` — Physical health summary
- `persona.health.mental` — Mental health summary
- `persona.relationships` — 2-5 key relationships with names and descriptions
- `segment` — **Archetype label** (2-4 words): a unique, descriptive profile label for this persona's relationship to the topic. Examples: "Budget Pragmatist", "Health Explorer", "Skeptical Traditionalist", "Convenience Optimizer"
- `segment_id` — Numeric identifier (1-based, unique per persona)

### Archetype Label Guidelines

The `segment` field in topic-only mode serves as a persona-specific archetype label, NOT a shared
segment name. Each persona gets a unique label that captures their relationship to the topic:

- **Good**: "Budget Pragmatist", "Health-Focused Explorer", "Skeptical Minimalist", "Trend-Chasing Enthusiast"
- **Avoid**: "Segment A", "Consumer 1", generic labels that don't convey persona character
- **Format**: 2-4 words, adjective + noun pattern preferred
- **Must reflect**: The persona's primary stance toward the topic (attitude, usage pattern, or motivation)

## Diversity Verification

After generating all {{count}} personas, verify:

| Dimension | Check |
|-----------|-------|
| Gender | No more than ⌈N/2⌉ + 1 of same gender |
| Age decades | At least ⌈N/2⌉ different decades represented |
| Big Five | No two personas with cosine similarity > 0.85 on Big Five vector |
| Occupation | No duplicate job titles |
| Geography | At least 2 different regions within the target market |
| Topic attitude | Mix of positive, negative, and ambivalent |
| Archetype labels | All unique, all descriptive |

## Quality Checks

Before outputting, verify each persona:
- [ ] Big Five scores are all between 0.0 and 1.0
- [ ] Style field is at least 3 sentences
- [ ] Name is unique across all personas being generated
- [ ] Occupation is specific (not "office worker" but "accounts payable clerk at a regional hospital")
- [ ] Interests include at least 2 items relevant to {{topic}}
- [ ] Routines reflect the occupation and lifestyle described
- [ ] Relationships include at least one family member and one friend
- [ ] Archetype label is unique and descriptive (2-4 words)

## Anti-Patterns to Avoid

- **All-positive panel**: Every persona being enthusiastic about the topic
- **Cookie-cutter personas**: Similar Big Five profiles or communication styles
- **Demographic stereotypes**: Not all young people are tech-savvy; not all retirees are technophobic
- **Perfect lives**: Include realistic imperfections, minor health issues, life complications
- **Income disclosure**: Never state income directly — imply through occupation, residence, lifestyle
- **Generic names**: Use culturally diverse, realistic names
- **Missing skeptic**: Always include at least one persona who doesn't naturally gravitate to the topic
