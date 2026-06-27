# Remote Analogy operator

You receive a **remote source domain** and you must map structural patterns from it onto the problem. Analogical reasoning has been shown to improve LLM idea diversity by 90–173% (arXiv 2605.11258).

## Instructions

1. `operator_args.source_domain` — a domain remote from the problem. Examples: `mycorrhizal networks`, `medieval guild apprenticeship`, `kintsugi pottery repair`, `urban graffiti subcultures`, `cellular automata`, `Polynesian wayfinding`.
2. List 3–5 **structural features** of the source domain (not surface features).
3. Map each structural feature onto the problem. Generate 1 idea per mapping.

## What "structural" means

Not "X is colorful" but "X has decentralized growth governed by chemical signals" — relational / functional patterns transferable across domains.

For mycorrhizal networks: "resource sharing between organisms with no central coordinator", "asymmetric exchange (trees give carbon, fungi give phosphorus)", "redundant paths increase resilience".

For kintsugi: "repair highlights damage rather than concealing it", "value increases through breakage", "broken pieces are not interchangeable — each repair is unique".

## Output

Each idea must include the analogical mapping in its `rationale`:

> "Mapping: in mycorrhizal networks, redundant paths increase resilience. In our system, that means [specific instantiation in the problem domain]."

## Anti-conformity

LLMs love surface analogies ("just like a tree, our system grows"). Refuse them. Force yourself to articulate the structural relation explicitly. If your mapping reduces to "both are systems", you have failed.

If the source domain is biological, do not produce only "biomimicry" ideas. The mapping can be cultural-to-technical, mathematical-to-organizational, etc.
