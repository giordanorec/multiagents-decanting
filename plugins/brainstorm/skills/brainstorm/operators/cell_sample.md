# Cell-Sample operator

You receive specific coordinates in the MAP-Elites archive (an **under-explored cell**) and your job is to produce ideas that **plausibly land in that cell**.

## Instructions

1. `operator_args.cell` — e.g., `[3, 7]`.
2. `operator_args.cell_meaning` — the human reading, e.g., `{"mechanism": "social", "horizon": "decade", "ethics-stance": "abolitionist"}`.
3. `operator_args.why_underfilled` — orchestrator's note, e.g., "No idea so far combines social mechanism with decade horizon."
4. Generate 3–6 ideas that *all* clearly fit the cell. Each idea's `rationale` must show why it satisfies each cell coordinate.

## Anti-conformity

This is the operator that directly fights mode collapse. Without it, the LLM crowds the same cells (the ones its prior is strongest in). Cell-sample forces it into corners it would never go.

Discipline:
- If your idea could plausibly land in any other cell, it's not specific enough.
- If you find yourself thinking "this cell is awkward, let me reinterpret it", **don't**. The cell is the constraint. Honor it.
- If after honest attempts you cannot generate even one plausible idea for the cell, return one idea with `tension_note: "Cell appears semantically inconsistent — recommend Boden transformation"`. This is signal to the morphologist.

## Output

```json
{
  "agent_id": "...",
  "operator": "CellSample",
  "target_cell": [3, 7],
  "target_meaning": {"mechanism": "social", "horizon": "decade"},
  "ideas": [
    {
      "essence": "Neighborhood energy-sharing coops with 10-year membership covenant.",
      "rationale": "Social mechanism (collective ownership), decade horizon (long-term covenant). Not consumer-purchase.",
      "intended_cell": [3, 7],
      ...
    }
  ]
}
```
