---
description: Show the status of the most recent brainstorming run
argument-hint: [run_id]
---

Print a short status report for run `$1` (or the most recent run if `$1` is missing).

1. Find the run directory (most recent under `./brainstorm-runs/` if no id).
2. Read `state/status.json`.
3. Print a compact summary:
   - Topic
   - Tier, phase, round X/R
   - Elapsed time
   - Ideas count, coverage %
   - Top 3 ideas (essence, elo)
   - Currently active agents

Do NOT read the full ideas.jsonl. Keep output under 30 lines.
