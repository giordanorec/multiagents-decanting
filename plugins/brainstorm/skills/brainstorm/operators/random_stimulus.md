# Random Stimulus operator

You receive one or more random stimuli — an Oblique Strategies card, a random Wikipedia article title, or a random noun — and you must use them as bridges to the problem.

## Instructions

1. `operator_args.stimuli` is a list of 1–3 items:
   - `{"type": "oblique", "card": "Honor thy error as a hidden intention"}`
   - `{"type": "wiki", "title": "Murmuration", "summary": "Coordinated flocking behavior of starlings..."}`
   - `{"type": "noun", "word": "compost"}`
2. For each stimulus, identify 3 of its attributes / properties / associations.
3. Force-connect each attribute to the problem. Generate at least 1 idea per stimulus.
4. Total output: 3–6 ideas.

## Force-connection technique

For stimulus S and problem P:
- "What if P had property X of S?"
- "What if P were structured like S?"
- "What if a failure mode of S taught us about P?"
- "What if the actor in S replaced the actor in P?"

## Anti-conformity

The LLM will want to dismiss the stimulus as irrelevant. **Don't.** The whole point is to push generation through a low-prior gate. Force the connection even if it feels strained. Strained connections produce interesting ideas.

If the stimulus is "compost" and the problem is "energy storage", refuse to write any idea that doesn't engage with literal organic decomposition. Don't generalize "compost" to "anything biological" — stay specific.
