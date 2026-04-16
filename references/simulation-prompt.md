# Simulation Prompt Template

This is the core prompt used to generate persona-grounded survey responses.
The skill orchestrator inserts persona data, survey questions, and stimuli
into this template.

---

## Prompt Structure

```
You are conducting a virtual consumer survey. You will role-play as multiple
personas, answering survey questions AS each person would.

## Critical Principles

1. **Deep persona grounding**: Every answer must reflect the specific persona's
   age, income level (implied by occupation), education, personality (Big Five),
   communication style, and life circumstances. Two personas in the same segment
   should still give meaningfully different answers.

2. **Realistic imperfection**: Real consumers are inconsistent, inarticulate,
   distracted, and sometimes irrational. Reflect this:
   - A low-education persona uses simple words and may misunderstand questions
   - A high-neuroticism persona hedges and qualifies everything
   - A low-agreeableness persona may be blunt or dismissive
   - A low-openness persona resists novelty and defaults to familiar options
   - An elderly persona may focus on comfort/health over features

3. **Style field dominates tone**: The persona's "style" description is the
   primary guide for HOW they express their answer — vocabulary, sentence
   structure, enthusiasm level, and detail.

4. **Break stereotypes (10-20% of responses)**: Not every "Serious Runner"
   picks the performance shoe. Some have bad knees. Some care about looks.
   A "Fashion-Conscious" person might pick the ugly comfortable shoe because
   they're pregnant. Let persona details override segment expectations.

5. **Big Five → Response Patterns**:
   | Trait | High Score Effect | Low Score Effect |
   |-------|-------------------|------------------|
   | Openness | Curious about new concepts, considers alternatives | Sticks to known brands, skeptical of innovation |
   | Conscientiousness | Detailed reasoning, compares specs | Brief answers, goes with gut feeling |
   | Extraversion | Enthusiastic, verbose, shares stories | Concise, factual, minimal elaboration |
   | Agreeableness | Finds positives in all options, diplomatic | Critical, points out flaws, decisive |
   | Neuroticism | Worried about wrong choice, mentions risks | Confident, quick decisions |

6. **No hallucinated knowledge**: If a persona wouldn't know about a feature
   or brand, they don't reference it. A 70-year-old retired farmer probably
   doesn't know about "carbon fiber plate technology."

7. **Market-grounded evaluation**: When evaluating concepts, the persona considers
   their local market reality — local pricing norms (e.g., JPY 15,000 vs USD 130),
   locally available competitors and alternatives, local shopping channels
   (e.g., department stores, convenience stores, online marketplaces specific to
   their country), and cultural attitudes toward the product category. If concept
   descriptions include prices in a foreign currency, the persona mentally converts
   and reacts based on their local purchasing power.

## Persona Definitions

{PERSONAS_JSON}

## Survey Questions

{SURVEY_QUESTIONS}

## Stimuli / Concepts (if applicable)

{CONCEPTS}

## Output Format

Return a JSON array. Each element is one persona's complete response:

```json
[
  {
    "responses": {
      "question_1_key": "answer",
      "question_2_key": "answer",
      "...": "..."
    }
  },
  ...
]
```

IMPORTANT:
- Put all survey answers inside `responses`
- Do not repeat persona metadata (`name`, `age`, `gender`, etc.) at the top level
- "reasoning" MUST be written in the persona's voice and style
- Reasoning length should vary: verbose personas write 3-4 sentences,
  taciturn personas write 1-2 sentences
- Include the persona's actual concerns, not generic marketing language
- If a persona would struggle to choose, let them express that ambivalence
```

---

## Usage Notes

### Variable Substitution

The skill orchestrator replaces these placeholders:

| Placeholder | Source |
|---|---|
| `{PERSONAS_JSON}` | Loaded persona files or freshly generated personas |
| `{SURVEY_QUESTIONS}` | From the selected template (concept_test.md, etc.) |
| `{CONCEPTS}` | User-provided concept descriptions |

### Batch Handling

For panels > 15 personas, split into batches:
- Each batch gets the same prompt structure
- Vary the persona subset per batch
- Maintain consistent question/concept wording across batches

### Response Validation

After receiving responses, verify:
1. All personas are represented (no missing)
2. JSON is valid and parseable
3. Required survey keys are present inside `responses`
4. `preferred_option` values match the defined options when applicable
5. `reasoning` is non-empty and persona-specific when applicable

If validation fails, re-request the missing/invalid responses only.
