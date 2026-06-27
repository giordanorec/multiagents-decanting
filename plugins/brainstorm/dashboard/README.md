# Ideation Dashboard

Single-file-ish, framework-free live dashboard for the multi-agent ideation
system. Polls `./state/status.json` and tails `./state/events.jsonl` to render
ideas being generated, merged, critiqued, promoted and bifurcated in real time.

## Quick start

The dashboard expects to live **inside a run directory** so that relative paths
resolve to `./state/*`. The typical layout is:

```
runs/
  run_2026_06_25/
    state/
      status.json
      events.jsonl
      ideas.jsonl
      archive.json
      embeddings.jsonl       (optional — enables UMAP drawer)
    dashboard/
      index.html
      style.css
      app.js
      start.bat / start.sh
```

Launch with the bundled scripts:

- **Windows:** double-click `start.bat`
- **macOS / Linux:** `bash start.sh`

Either script runs `python -m http.server 8765` from the run directory and
opens `http://localhost:8765/dashboard/index.html` in your browser.

## What each panel shows

### Header
- **run / tier / phase / round / elapsed / ideas** — from `status.json`.
- **Coverage gauge** — `coverage_pct` percentage of the MAP-Elites archive
  that has been filled.
- **Drawer buttons** open four overlays (see below).

### Center: force graph
- One node per idea (color by cluster). Lineage links connect parent to
  child. Active links emit travelling particles.
- Node radius scales with elo. Promoted ideas show a gold ring.
- Nodes whose `last_referenced_at` is older than 60s fade toward 25% alpha.
- Click a node to open its **Lineage** drawer.

### Right column
- **Agents** — live feed of agents: name, persona snippet, current task, and
  a colored dot for active/idle.
- **Top Ideas** — best 5 by elo (essence, cluster, score). Click to focus
  its lineage. The panel breathes faintly so you know the page is alive.
- **Structural Gaps** — cells the MAP-Elites archive is missing, with a
  hint about which mechanism/horizon axes are empty.

### Footer
- **Timeline** — horizontal bars: phases on the top track (teal), rounds on
  the bottom (amber).

### Drawers
- **UMAP** — runs `umap-js` over `state/embeddings.jsonl` (skipped if file
  absent).
- **Parallel** — ECharts parallel coordinates over current top ideas.
- **Coverage** — 2D heatmap of `state/archive.json` projected to its first
  two axes (averages collapsed dimensions).
- **Lineage** — tree of ancestors for the focused idea.

## Event animations

| Event              | Animation                                              |
|--------------------|--------------------------------------------------------|
| `idea_created`     | white halo + grow from 0 to target size (300 ms)        |
| `idea_merged`      | particles from parents to child, then parents ghost     |
| `idea_bifurcated`  | radial burst at source, two children launched          |
| `idea_promoted`    | golden glow (1 s), node size +20%                       |
| `idea_critiqued`   | pulsing ring — red for black-hat, teal for minority    |
| `axes_transformed` | full graph dim + restore                                |
| `tournament_result`| winner pulses, loser dims                              |
| `phase_transition` | toast at top                                            |
| `round_started`    | round counter flashes; new bar on timeline             |

Every event is also `console.log`-ed for debugging.

## File expectations

The dashboard reads four files from `./state/` — see the JSON shapes in the
project SKILL spec. Missing files are tolerated:

- `status.json` missing → header and panels stay in their loading state.
- `events.jsonl` missing → no animations, but no errors.
- `archive.json` missing → Coverage drawer shows "archive unavailable".
- `embeddings.jsonl` missing → UMAP drawer shows "embeddings unavailable".

## Theme

A sun button toggles dark / light. Choice is persisted in `localStorage`.
