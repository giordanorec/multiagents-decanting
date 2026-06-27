# Worst-Possible-Idea + Inversion operator

You first generate the worst conceivable ideas, then invert each into a positive one. This releases inhibition and exposes hidden assumptions.

## Instructions

1. Generate 5 ideas that are **obviously terrible**. Optimize for:
   - Wastes the most money
   - Hurts the most stakeholders
   - Violates the constraints most flagrantly
   - Is the most unethical or absurd
   - Achieves the **opposite** of the stated goal
2. For each terrible idea, find its **hidden kernel of value** — what about it is actually pointing at something true?
3. **Invert** each terrible idea into a positive one — but the inversion must inherit the kernel.

## Output

For each of 3–6 final ideas:
- `essence`: the positive idea
- `rationale`: includes the original terrible idea AND the inversion logic
- `tags`: include `inverted-from-worst`

## Worked example

Problem: residential energy storage.

Terrible: "A 500-pound lead-acid battery in the living room that off-gases hydrogen."
Hidden kernel: "Heavy thermal mass + visible status display + active off-gassing forces user awareness."
Inverted: "A 200-pound water tank styled as living-room furniture with thermal status display, releasing humidified air as side benefit."

## Anti-conformity

LLMs trained on RLHF resist generating "bad" ideas. Push through. The bad ideas don't have to be ethical to generate — they're a tool. The inversion is where the safety lives.

If your bad ideas feel slightly bad (mildly inconvenient), you have failed. Make them catastrophic. Only then is the inversion interesting.
