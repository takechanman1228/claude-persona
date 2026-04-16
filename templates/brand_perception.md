# Brand Perception Survey Template

## Scenario

We'd like to understand your awareness and perceptions of brands
in the {{category}} category.

## Brand List

{{brands}}

## Questions

### Q1: Unaided Awareness
Without looking at any list, name the first 3 brands that come to mind
when you think of {{category}}.

### Q2: Aided Familiarity
For each brand in the list above, indicate:
- "know_well" — I know this brand and have opinions about it
- "heard_of" — I've heard the name but don't know much
- "unknown" — Never heard of it

### Q3: Brand Buckets
Sort the brands you know into:
- "like" — Brands I have a positive impression of
- "dislike" — Brands I have a negative impression of
- "neutral" — Know them but no strong feeling

### Q4: Consideration Set
If you were buying {{category}} today, which brands would you
seriously consider? List up to 5.

### Q5: Brand Associations
For your top 2 favorite brands, describe in 1-2 sentences what
each brand means to you — what image or feeling comes to mind.

## Output Keys

Each persona response must include:
- `unaided_awareness`: array of up to 3 brand names
- `aided_familiarity`: object with brand_name → "know_well"|"heard_of"|"unknown"
- `brand_buckets`: object with "like", "dislike", "neutral" arrays
- `consideration_set`: array of up to 5 brand names
- `brand_associations`: object with brand_name → text description
