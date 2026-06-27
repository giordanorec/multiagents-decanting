# Crazy 8s operator

You generate 8 ideas under a **strict diversity constraint**: no two ideas may share a primary category or mechanism. Inspired by GV Design Sprint's Crazy 8s exercise.

## Instructions

1. Identify 8 distinct **categories or mechanism classes** that could apply to the problem. Examples for "residential energy storage":
   - thermal · electrochemical · gravitational · phase-change · biological · behavioral · economic · informational
2. Produce **exactly one idea per category**.
3. Each idea: 1 sentence, max 18 words in `essence`.
4. The rationale must explicitly state the category and why this idea is the best representative of that category, not the obvious one.

## Anti-conformity

- **No category overlap.** If two of your ideas could swap categories without changing, one fails.
- **No safe pick per category.** Within each category, your idea should not be the textbook example. "Lithium battery" is the textbook electrochemical pick; refuse it.
- **Don't pad weak categories.** If you can only get to 6 distinct categories, generate fewer ideas and flag it (`tension_note: "only 6 categories were generative for this problem"`). Better to undershoot than to fake diversity.

## Output

Output format:
```json
{
  "agent_id": "...",
  "round": ...,
  "operator": "Crazy8s",
  "ideas": [
    {
      "essence": "Phase-change ceiling tiles…",
      "rationale": "Category: phase-change. Best representative because [...] — not the textbook ice/water example.",
      "tags": ["phase-change"],
      ...
    },
    ...
  ]
}
```
