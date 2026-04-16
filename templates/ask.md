# Open Research Question: {{category}}

You've been asked: **{{user_question}}**

Answer honestly, in your own voice. Draw on your personal circumstances,
habits, and perspective. There are no right or wrong answers.

**Q1 — Direct answer**: In 2-3 sentences, what is your direct answer to this question?

**Q2 — Reasoning**: In 2-4 sentences, explain the specific reasons behind your
answer. Be concrete and personal — reference your own life, not generic opinions.

**Q3 — Themes**: Name 1-4 short phrases (each under 6 words) that capture the
underlying themes or tensions shaping your thinking.
Examples: "lack of size guidance", "trust the brand", "afraid of returns".

**Q4 — Emotion**: In one word, what is the dominant emotional tone of your answer?
Examples: "frustrated", "curious", "indifferent", "excited", "skeptical", "conflicted".

Return a single JSON object with these exact keys:

```json
{
  "short_answer": "...",
  "reasoning": "...",
  "themes": ["...", "..."],
  "emotion": "..."
}
```
