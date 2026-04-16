# Usage Habits Survey Template

## Scenario

We'd like to understand how you currently use {{category}} products
in your daily life.

## Occasions

{{occasions}}

## Questions

### Q1: Usage Frequency
For each occasion listed, how often do you use {{category}} products?
- "daily" — Every day or almost every day
- "weekly" — A few times a week
- "monthly" — A few times a month
- "rarely" — A few times a year
- "never" — Not applicable to me

### Q2: Current Product
What {{category}} product do you currently use most? Include brand
and approximate price if you remember.

### Q3: Purchase Channel
Where did you last buy a {{category}} product?
(e.g., online retailer, brand website, physical store, second-hand)

### Q4: Decision Factors
Rank these factors by importance when choosing a {{category}} product:
{{decision_factors}}
(1 = most important, assign each a unique rank)

### Q5: Pain Points
What frustrates you most about {{category}} products you've used?
What's missing from the market?

### Q6: Information Sources
When researching a {{category}} purchase, where do you look first?
(e.g., friends/family, online reviews, social media, in-store, brand website)

## Output Keys

Each persona response must include:
- `usage_frequency`: object with occasion → frequency string
- `current_product`: text (brand, model, price)
- `purchase_channel`: text
- `factor_ranking`: object with factor → rank integer
- `pain_points`: text (1-3 sentences)
- `info_sources`: array of up to 3 sources
