# Pipeline reference (long-form)

This document supplements `SKILL.md`. It explains the WHY behind each phase so an LLM running the skill can make judgment calls that the prescriptive instructions don't anticipate.

## The conformity problem

Default LLM brainstorming converges to "average ideas" because of overlapping failure modes documented in 2024–2026:

- **Mode collapse / typicality bias** — RLHF compresses output toward a small set of "typical" responses. (Verbalized Sampling, arXiv 2510.01171.)
- **Sycophancy** — agreement with stated user position.
- **Homogenization / artificial hivemind** — multiple agents from the same base model converge faster, not slower. (arXiv 2510.22954.)
- **Knowledge collapse** — epistemic diversity shrinks across population usage. (arXiv 2510.04226.)
- **Ideation-execution gap** — LLM ideas score higher than human ideas at ideation but worse after execution. (arXiv 2506.20803.)

Each phase of the pipeline targets one or more of these failure modes:

| Failure | Counter-mechanism |
|---|---|
| Mode collapse | Verbalized sampling, min-p, cycling operators |
| Sycophancy | Devil's-advocate critic round |
| Homogenization | Interview-grounded personas, cosine<0.7 check |
| Convergence to mean | MAP-Elites archive (per-cell elite, not global) |
| Premature consensus | Minority-voice critic; rotated judges |
| Stagnation | Boden transformational rewriting of axes |
| Hidden trade-offs | Pareto front over (novelty × feasibility × impact) |
| Ideation-execution gap | Each top idea ends with a 3-paragraph design sketch |

## Phase-by-phase rationale

### Phase 0 — Socratic

Why before generation? The user's framing carries hidden assumptions. If the morphologist were to decompose them as given, all axes would inherit those assumptions. Socratic surfaces the assumptions so morphologist can choose to break some.

### Phase 1 — Morphology

The single highest-leverage step. The axes ARE the design space. Bad axes = exploration of a tiny corner of possibility. Good axes = wide, generative, orthogonal.

Tests for "good axes":
- Could a child reading the axis names guess wildly different solutions by changing one axis? If yes, good.
- Are any two axes statistically correlated in your head? If yes, redo.
- Did the user's framing dictate any axis? If yes, replace that one.

### Phase 2 — Persona forge

Personas are NOT decoration. They are the bias generators. Without interview-grounded personas, the divergent agents all collapse onto the base model's voice.

The cosine<0.7 check is critical: LLM-generated personas drift toward the LLM's prior. Without active diversity enforcement, all 8 "personas" end up being polite progressive professionals.

### Phase 3a — Divergence

Operators are external constraints that push the model out of its prior. They are NOT optional flavors. An agent that "interpreted SCAMPER loosely" silently collapses to typical output.

The cell hint (target an under-explored MAP-Elites cell) is the strongest active diversity lever — it directly steers the model into corners it would not visit.

### Phase 3b — Archive placement

The archive is the memory of where we've been. Without it, ideas crowd predictable cells while empty regions stay empty.

Cell placement is approximate (LLM-judged via embeddings + axis-value similarity). It's good enough.

### Phase 3c — Critique

Two-critic system is intentional:
- **Black hat** finds flaws (the idea's weakness).
- **Minority voice** finds what frame is missing (the idea's blind spot).

These are different errors. Conflating them produces weaker critiques.

Critiques **do not delete ideas**. They get attached. The evolution step uses them as input for crossovers and mutations.

### Phase 3d — Evolution

- Crossover hybridizes ideas from different clusters → forces cross-pollination.
- Mutation SCAMPERs a high-novelty idea → exploits a good region.
- **Boden transformation** (when coverage saturates) → rewrites the axes themselves. This is the closest we can get to Boden's "transformational creativity": ideas that change the rules of the space, not just move within it.

### Phase 3e — Tournament

Why Elo with rotated judges (not soft sum)?

Soft sums (e.g., ICE = Impact × Confidence × Ease) hide trade-offs and reward middle-of-the-road ideas. Elo with rotated judges produces a ranking that is robust to individual judge biases.

Each round, the judge persona changes. After enough rounds, the Elo reflects the multi-perspective consensus.

### Phase 4 — Pareto

Final selection. Pareto over (novelty × feasibility × impact) exposes the trade-offs the user must make. Knee-point selection picks the "best compromise" but the user sees the full front.

### Phase 5 — Meta-review

Long-form synthesis. Each top idea gets a 3-paragraph design sketch — this addresses the ideation-execution gap by forcing the synthesizer to imagine implementation.

## When the system fails gracefully

- **MCP server down**: degrade to verbal archive (LLM judges cell placement directly from text). Lose precision, keep direction.
- **Persona regeneration loops**: after 3 attempts to get cosine<0.7, accept the closest and warn user.
- **Operator-persona conflict**: divergent agent reports `tension_note`; orchestrator surfaces it but doesn't retry. Tension is signal.
- **Judge disagreement**: high entropy in Elo deltas across judges = idea is genuinely controversial; show it as such.

## What the dashboard reveals that the report doesn't

The report compresses a multi-hour run into 7 ideas. The dashboard exposes:
- The dead branches (ideas that died early)
- The clusters that never produced a Pareto-front winner
- The structural gaps that remain unfilled — sometimes more interesting than the filled cells
- The agents whose ideas survived disproportionately (which personas were most generative?)

A user who watches the dashboard learns more about *their problem* than they learn from the final report.
