# Concept Test Survey Template

## Scenario

You are shopping for {{category}}. You've been shown three product concepts
and asked to evaluate them.

## Concepts

{{concepts}}

## Questions

### Q1: Preferred Option
Which concept do you prefer most? Choose one: A, B, or C.

### Q2: Reasoning
In your own words, explain why you chose that option. What about it appeals
to you, and what made you pass on the other options? Be specific about the
features or qualities that matter to you personally.

### Q3: Purchase Likelihood (1-5)
How likely would you be to actually buy your preferred option?
1 = Definitely not buying
2 = Probably not
3 = Maybe, need more info
4 = Probably yes
5 = Definitely buying

### Q4: Improvement Suggestion
What one thing would you change about your preferred concept to make it even better?

## Output Keys

Each persona response must include:
- `preferred_option`: "A", "B", or "C"
- `reasoning`: 2-4 sentences in persona's voice
- `purchase_likelihood`: integer 1-5
- `improvement`: 1-2 sentences
