# Price Sensitivity Survey Template

## Scenario

You are considering purchasing the following product:

{{product_description}}

We'd like to understand how price affects your purchase decision.

## Price Points

{{price_points}}

## Questions

### Q1: Maximum Willingness to Pay
What is the absolute maximum you would pay for this product?
Give a specific dollar amount.

### Q2: Purchase Intent at Each Price
For each price point listed above, rate your purchase likelihood:
1 = Definitely not buying
2 = Probably not
3 = Maybe
4 = Probably yes
5 = Definitely buying

### Q3: Value Perception
At the lowest price point, would you worry about the quality?
At the highest price point, what would you need to see to justify it?

### Q4: Competitive Reference
What do you currently pay for a similar product, or what would you
expect to pay based on your experience?

### Q5: Price-Quality Tradeoff
If you had to choose between a cheaper option with fewer features
and an expensive option with all features, which would you lean toward?
Explain your reasoning.

## Output Keys

Each persona response must include:
- `max_wtp`: integer (dollar amount)
- `intent_by_price`: object with price_point → integer 1-5
- `value_perception`: text (2-3 sentences)
- `competitive_reference`: integer (dollar amount) or "unsure"
- `price_quality_preference`: "cheaper"|"expensive"|"depends"
- `reasoning`: 2-3 sentences in persona's voice
