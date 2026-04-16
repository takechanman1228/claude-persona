# One-Pager Report Template

The default report format for topic-only mode. Claude generates this directly
from `results.json` without running Python scripts.

```markdown
# [Survey Type]: [Topic] — Virtual Research Report

**Date**: YYYY-MM-DD | **Panel**: N personas

## Panel Overview
| # | Name | Age | Occupation | Profile | Preferred |
|---|------|-----|------------|---------|-----------|
| 1 | ... | ... | ... | ... | ... |

## Key Findings
1. [Most important insight]
2. [Second insight]
3. [Third insight]

## Profile Analysis
**[Profile label]** (Name, Age):
[2-3 sentences on this persona's response pattern, key drivers, and notable choices]

**[Profile label]** (Name, Age):
[2-3 sentences]

...

## Notable Verbatims
> "[Direct quote from reasoning field]" — Name, Age, Occupation

> "[Another quote]" — Name, Age, Occupation

## Caveats
- Virtual panel of N personas; directional only
- Not statistically representative; use for hypothesis generation
- AI-generated responses may exhibit positivity bias
```

## Report Generation Rules

- **Key Findings**: Synthesize 3-5 insights from the response data. Focus on
  patterns, splits, and surprises — not summaries of each persona.
- **Profile Analysis**: One paragraph per persona. Highlight what drove their
  choice and how their personality/background influenced it.
- **Notable Verbatims**: Pick 2-3 quotes from the most relevant free-text fields
  for the survey type (`reasoning`, `pain_points`, `brand_associations`, etc.).
  Choose quotes that sound authentic and persona-specific.
- **Caveats**: Always include. Adjust the sample size caveat to match actual N.
