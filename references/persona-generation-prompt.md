# Persona Generation Prompt

Generate realistic, survey-ready consumer personas for the given category and segment.

## Instructions

You are a population researcher creating detailed consumer personas for virtual market research.
Generate **{{count}}** personas for the segment defined below. Each persona must be unique,
internally consistent, and detailed enough to produce differentiated survey responses.

## Market Context

**Target Market**: {{market}}

Generate personas who are **residents of this market**. Use local names, local cities/regions,
local currency in lifestyle details, culturally appropriate occupations and behaviors, and
communication styles that reflect how people in this market actually talk. For non-Latin-script
markets, use romanized names and addresses (JSON must be ASCII-safe).

If `{{market}}` appears unresolved, default to United States.

## Category & Segment

**Category**: {{category}}
**Segment**: {{segment_name}}
**Segment Description**: {{segment_definition}}
**Demographic Priors**: {{demographic_priors}}

## Slot Specifications (from Sampling Plan)

{{slot_specs}}

If slot specifications are provided above, each persona MUST adhere to its
slot's constraints (age_bucket, gender, occupation_tier, geography_type,
region_hint, category_stance, ethnicity_hint). The slot values are mandatory
anchors — your job is to flesh out the skeleton into a rich, full persona.

- `age_bucket` "30s" → choose a specific age between 30-39
- `occupation_tier` constrains the type of job, not the exact title — be creative
  with the specific title within the tier
- `geography_type` + `region_hint` constrain the residence — choose a specific city
- `category_stance` constrains the persona's attitude toward {{category}}
- `ethnicity_hint` guides name and cultural background choices

If `{{slot_specs}}` appears unresolved or empty, ignore this section and
generate personas freely using the diversity requirements below.

## Exclusion List (Cross-Segment Deduplication)

{{exclusion_list}}

If an exclusion list is provided above, you MUST NOT reuse any first name,
surname, or occupation title from that list. Choose completely different
names and job titles to ensure panel-wide uniqueness.

If `{{exclusion_list}}` appears unresolved or empty, ignore this section.

## Output: Full Persona JSON

For each persona, produce a complete JSON object following the schema in `persona-schema.md`.
Every persona MUST include:

### Required Fields
- `persona.name` — Realistic full name (unique across the panel)
- `persona.age` — Integer, within the segment's age range but with variation
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
- `segment` — The segment name (top-level field)
- `segment_id` — Numeric segment identifier (top-level field)

## Diversity Requirements (CRITICAL)

Within this batch of {{count}} personas for the **same segment**:

1. **Big Five Spread**: No two personas should have the same Big Five profile.
   Vary each dimension by at least 0.15 across personas.
   Include at least one high-neuroticism and one low-agreeableness persona.
2. **Age Spread**: Distribute across the segment's age range. No more than 2 personas in the same 5-year bracket.
3. **Gender Mix**: At least 40% of the less-represented gender (unless the segment naturally skews).
4. **Geography**: At least 3 different regions within the target market. Mix urban, suburban, rural.
5. **Occupation Variety**: No two personas with the same job title.
6. **Ethnicity/Background**: Representative mix — not all the same ethnic background.
7. **Education**: Mix of levels (some with advanced degrees, some without college).
8. **Style Variation**: Communication styles must differ — some terse, some verbose, some formal, some casual.

## Quality Checks

Before outputting, verify each persona:
- [ ] Big Five scores are all between 0.0 and 1.0
- [ ] Style field is at least 3 sentences
- [ ] Name is unique across all personas being generated
- [ ] Age falls within the segment's demographic priors
- [ ] Occupation is specific (not "office worker" but "accounts payable clerk at a regional hospital")
- [ ] Interests include at least 2 items relevant to {{category}}
- [ ] Routines reflect the occupation and lifestyle described
- [ ] Relationships include at least one family member and one friend

## Anti-Patterns to Avoid

- **Cookie-cutter personas**: All personas in a segment sounding/feeling the same
- **Demographic stereotypes**: Not all young people are tech-savvy; not all retirees are technophobic
- **Perfect lives**: Include realistic imperfections, minor health issues, life complications
- **Income disclosure**: Never state income directly — imply through occupation, residence, lifestyle
- **Generic names**: Use culturally diverse, realistic names (not "John Smith" and "Jane Doe")
