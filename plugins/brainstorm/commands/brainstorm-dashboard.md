---
description: Open the dashboard for a brainstorming run
argument-hint: [run_id]
---

Launch the dashboard for run `$1` (or the most recent run if `$1` is missing).

1. List `./brainstorm-runs/` and pick the most recent if no id given.
2. Start `python -m http.server 8765` in the run directory using `Bash(run_in_background=true)`.
3. Print: `Dashboard live: http://localhost:8765/dashboard/index.html`.
4. On Windows, also run `start http://localhost:8765/dashboard/index.html` to auto-open the browser.
