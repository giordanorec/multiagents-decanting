# claude-brainstorm-multiagent

Multi-agent ideation skill for Claude Code that fights LLM conformity through **structural diversity** — morphological decomposition, Quality-Diversity (MAP-Elites), explicit adversaries, and Pareto convergence — with a **live force-graph dashboard** that shows ideas being born, merged, critiqued, promoted, and bifurcated in real time.

## Why this exists

Default LLM brainstorming converges to "average ideas" because:

- Post-RLHF mode collapse pushes outputs toward typical responses
- Multiple agents from the same base model amplify each other ("artificial hivemind", arXiv 2510.22954)
- Scalar scoring (ICE/RICE sums) hides trade-offs and rewards mediocrity

This plugin attacks each failure mode explicitly:

| Failure mode | Counter-mechanism |
|---|---|
| Mode collapse | Verbalized sampling + min-p + cycling operators |
| Persona homogenization | Interview-grounded personas with cosine < 0.7 |
| Convergence to mean | MAP-Elites archive (best per region, not best overall) |
| Premature consensus | Devil's-advocate + minority-voice critics every round |
| Judge bias | Rotated LLM judges in Elo tournament |
| Stagnation | Boden transformational rewriting of morphological axes |
| Hidden trade-offs | Pareto front over (novelty × feasibility × impact) |

## Method

A Double Diamond pipeline with Co-Scientist-style inner loop:

```
Phase 0  Socratic clarify          (1 agent)
Phase 1  Morphological decompose   (1 agent)      → defines the design space
Phase 2  Persona forge             (1 agent)      → N orthogonal personas
Phase 3  Ideation rounds (loop R rounds):
   3a    Divergent generation      (N parallel agents, cycling operators)
   3b    Embed + archive           (MAP-Elites placement)
   3c    Cluster + KJ              (HDBSCAN)
   3d    Adversarial critique      (Black Hat + Minority Voice)
   3e    Evolution                 (crossover, mutation, Boden transformation)
   3f    Tournament                (Elo with rotated judges)
Phase 4  Pareto front extraction
Phase 5  Meta-review + design docs
```

Operators that the divergent agents cycle through:

- **SCAMPER** (7 mutation types)
- **Lateral PO** (provocations)
- **Random stimuli** (Wikipedia / Oblique Strategies cards)
- **Remote analogy** (cross-domain, biomimicry)
- **Worst-possible-idea + inversion**
- **Crazy 8s** (8 quick ideas, no category overlap)
- **Verbalized sampling** (distribution with probabilities)
- **Cell sampling** (forced into under-explored MAP-Elites cells)

## Intensity tiers

| Tier | Time | Personas (N) | Rounds (R) | Archive | Tournament |
|------|------|-------------|------------|---------|------------|
| `instant`  | < 1 min   | 1  | 1   | off       | top-3      |
| `quick`    | 5–10 min  | 3  | 2   | 5×5       | top-5      |
| `standard` | ~1 h      | 6  | 5   | 8×8       | Elo 30     |
| `deep`     | several h | 8  | 12  | 10×10     | Elo 100 + Pareto |
| `marathon` | 1 day     | 12 | 30  | 12×12 + Boden | Elo 300 + adversarial |
| `epic`     | several d | 16 | 100+ | 16×16 + transforms every 20 | Elo 1000 |

## Installation

### 1. Install the plugin

From a marketplace (recommended):

```
/plugin marketplace add giordanorec/claude-brainstorm-multiagent
/plugin install claude-brainstorm-multiagent
```

Or directly from a local copy:

```
/plugin install file://path/to/plugin
```

### 2. Requirements

- Claude Code v2.1.172 or later
- Python 3.10+ available on PATH (the MCP server uses `uvx`; install via `pip install uv` if needed)
- For the dashboard: a modern browser. The launcher uses `python -m http.server` (already covered if you have Python).

### 3. First run

```
/brainstorm standard
```

then enter your topic when prompted, e.g.:

> "New directions for renewable energy storage at residential scale."

The skill creates a run directory under `runs/<timestamp>-<slug>/` and prints a URL like `http://localhost:8765/dashboard.html` — open it to see ideas being generated live.

## Dashboard

Single-file HTML using `force-graph` (Vasco Asturiano) + ECharts via CDN. No build step.

Panels:

- **Center**: force-directed graph of ideas. Node size = Elo, color = cluster, glow = recent activity, particles = lineage flow.
- **Right top**: Agents activity feed — "div_3 is applying SCAMPER:Combine to i_0042".
- **Right middle**: Top-5 ideas (sentence each).
- **Right bottom**: Coverage gauge + structural-gap suggestions.
- **Footer**: timeline of round events.
- **Drawers**: semantic UMAP, parallel coordinates, MAP-Elites coverage heatmap, lineage tree.

Animations:

- `idea_created` — flash + grow
- `idea_merged` — convergent particles
- `idea_bifurcated` — radial burst
- `idea_promoted` — golden glow
- `idea_critiqued` — pulsing ring in critic's color
- Old ideas decay to ghost opacity but reappear when cited

## Distribution

The plugin is self-contained. To share:

1. Push this directory to a GitHub repo.
2. Add a `marketplace.json` at the repo root listing this plugin.
3. Others install with `/plugin marketplace add <user>/<repo>`.

A template `marketplace.json` is included.

## Research underpinnings

See `research/` for the full literature survey. Key sources:

- Verbalized Sampling (arXiv 2510.01171) — anti-mode-collapse
- Artificial Hivemind (arXiv 2510.22954) — why naive multi-agent fails
- Co-Scientist (DeepMind 2024) — Elo tournament + evolution
- MAP-Elites (Mouret & Clune 2015) — quality-diversity
- Stanley & Lehman "Why Greatness Cannot Be Planned" — novelty over objectives
- Park et al. "Generative Agents" (Stanford 2023) — interview-grounded personas
- Boden "The Creative Mind" — combinatorial/exploratory/transformational

## License

MIT.
