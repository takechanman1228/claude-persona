# Segment Inference Prompt

Given a survey topic, infer 3-4 consumer segments that would provide meaningful differentiation in survey responses.

## Instructions

You are a market research strategist. Given the topic below, define 3-4 **behavior-based** consumer segments that:

1. Represent distinct usage patterns, motivations, or decision-making styles for this category
2. Would produce meaningfully different survey responses from each other
3. Cover the realistic spectrum of consumers (not just enthusiasts)
4. Are defined by **behaviors and attitudes**, not just demographics

## Topic

**Category**: {{category}}
**Context** (if provided): {{context}}

## Output Format

Return a JSON array of segment definitions. Each segment must include:

```json
[
  {
    "name": "Segment Name",
    "description": "1-2 sentence behavioral description. What defines this group's relationship with the category.",
    "demographic_priors": {
      "age_range": [min, max],
      "income_signal": "low | moderate | moderate-to-high | high | mixed",
      "urban_rural": "urban | suburban | rural | mixed"
    },
    "behavioral_markers": [
      "Key behavior 1 (e.g., frequency, channel, decision style)",
      "Key behavior 2",
      "Key behavior 3"
    ],
    "motivation": "Primary motivation or need state driving their category engagement"
  }
]
```

## Segment Design Rules

1. **Behavior-first, not demo-first**: "Daily ritual drinkers" not "Males 25-34"
2. **Mutually exclusive**: A real person would clearly belong to one segment
3. **Collectively exhaustive**: Cover at least 80% of the realistic consumer base
4. **Actionable**: Each segment should suggest different product/messaging strategies
5. **3-4 segments**: Fewer than 3 lacks nuance; more than 4 is hard to distinguish in small panels

## Examples

**Topic: Canned coffee**
- "Daily Ritual Drinker" — drinks 1-2 cans daily, treats it as a routine caffeine source
- "Convenience Seeker" — grabs canned coffee when fresh brew isn't available (commute, travel)
- "Health-Conscious Switcher" — considering or has switched from sugary drinks, reads labels
- "Taste Explorer" — tries new brands/flavors, influenced by social media and packaging

**Topic: Electric vehicles**
- "Early Adopter Enthusiast" — follows EV news, values technology and environmental impact
- "Practical Calculator" — comparing TCO vs gas, focused on range, charging infrastructure
- "Reluctant Considerer" — aware of EVs but skeptical, concerned about reliability/resale
