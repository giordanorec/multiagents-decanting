# Verbalized Sampling operator

Based on Verbalized Sampling (arXiv 2510.01171, Oct 2025), which gives 2–3× diversity gain without quality loss.

## Instructions

Instead of generating ideas freely, you first **explicitly enumerate the distribution** you would sample from, then deliberately pick low-probability tails.

1. List 8 "modes" of solution you could generate, with rough probabilities you'd assign each:
   ```
   - 0.32 — battery-based (obvious / typical)
   - 0.18 — thermal mass
   - 0.12 — behavioral / time-shifting
   - 0.10 — community-scale sharing
   - 0.10 — phase-change material
   - 0.08 — kinetic / mechanical
   - 0.06 — biological / fermentation
   - 0.04 — speculative / not-yet-real
   ```
2. Probabilities must sum to ~1.0 and reflect what the LLM's prior actually concentrates on.
3. **Pick the 3–6 LOWEST-probability modes** and generate one idea each.
4. State the mode and probability explicitly in `rationale`.

## Anti-conformity

The point is to force exploration of the tails. If your low-probability modes are still safe LLM territory ("blockchain"), expand the enumeration: you're not seeing your true distribution.

A good enumeration includes at least one mode you find personally uncomfortable / weird / unlikely to defend. Pick that one.

## Output

```json
{
  "agent_id": "...",
  "operator": "VerbalizedSampling",
  "distribution": {
    "battery": 0.32,
    "thermal_mass": 0.18,
    "behavioral": 0.12,
    "community": 0.10,
    "phase_change": 0.10,
    "kinetic": 0.08,
    "biological": 0.06,
    "speculative": 0.04
  },
  "ideas": [
    {
      "essence": "...",
      "rationale": "Mode: kinetic (prob 0.08). Picked because under-represented in baseline output.",
      ...
    },
    ...
  ]
}
```
