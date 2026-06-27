---
description: Resume an interrupted brainstorming run from its last checkpoint
argument-hint: [run_id]
---

Resume the brainstorming run with id `$1`.

Read `./brainstorm-runs/$1/state/status.json` and `./brainstorm-runs/$1/checkpoints/`. Determine the last completed phase/round and continue from there. Use the same tier configuration recorded in `status.json`.

If `$1` is missing, list all runs in `./brainstorm-runs/` with their topics and last status, and ask the user to pick one.
