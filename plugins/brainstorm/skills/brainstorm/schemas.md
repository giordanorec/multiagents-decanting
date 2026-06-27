# State file schemas — reference

All files live in `brainstorm-runs/<run_id>/state/`.

## `status.json`
Live snapshot polled by the dashboard every 1.5s. Atomic write only.

```json
{
  "run_id": "20260625-143010-renewable-storage",
  "topic": "New directions for renewable energy storage at residential scale",
  "tier": "standard",
  "phase": "divergent | clustering | critique | evolution | tournament | pareto | meta_review | done",
  "round": 3,
  "max_rounds": 5,
  "started_at": "2026-06-25T14:30:10Z",
  "elapsed_seconds": 1234,
  "ideas_count": 87,
  "ideas_active": 64,
  "clusters_count": 6,
  "coverage_pct": 0.42,
  "agents": [
    {"name": "div_1", "status": "active",
     "task": "SCAMPER:Combine on i_0034",
     "persona": "Maria, civil engineer",
     "started_at": "..."},
    {"name": "critic-black-hat", "status": "idle"}
  ],
  "top_ideas": [
    {"id": "i_0042", "essence": "Phase-change ceiling tiles…", "elo": 1620, "cluster": "thermal"}
  ],
  "structural_gaps": [
    {"cell": [3, 7], "axes": {"mechanism": "social", "horizon": "decade"}, "score": 0.0}
  ]
}
```

## `ideas.jsonl`
One JSON object per line. Append-only.

```json
{
  "id": "i_0042",
  "round": 3,
  "agent": "div_2",
  "persona": "Maria, civil engineer, anxious about climate",
  "operator": "SCAMPER:Combine",
  "parents": ["i_0010", "i_0028"],
  "text": "Phase-change ceiling tiles that store thermal energy from rooftop heat exchanger.",
  "rationale": "Combines passive thermal storage with PV-thermal hybrid panels.",
  "embedding_id": "e_0042",
  "archive_cell": [3, 5],
  "novelty_score": 0.72,
  "feasibility_score": 0.61,
  "impact_score": 0.83,
  "elo": 1500,
  "status": "active",
  "ts": "2026-06-25T14:32:11Z",
  "critiques": []
}
```

`status` ∈ `active | discarded | merged | promoted | superseded`.

## `events.jsonl`
Append-only timeline driving dashboard animations.

```json
{"ts": "2026-06-25T14:32:11Z", "type": "idea_created", "id": "i_0042", "agent": "div_2", "operator": "SCAMPER:Combine", "parents": ["i_0010", "i_0028"], "cell": [3, 5]}
{"ts": "...", "type": "idea_merged", "from": ["i_0010", "i_0028"], "to": "i_0050"}
{"ts": "...", "type": "idea_bifurcated", "from": "i_0042", "to": ["i_0060", "i_0061"]}
{"ts": "...", "type": "idea_promoted", "id": "i_0042", "reason": "pareto"}
{"ts": "...", "type": "idea_critiqued", "id": "i_0042", "critic": "black-hat", "summary": "Cost > $40/sqft"}
{"ts": "...", "type": "round_started", "round": 4}
{"ts": "...", "type": "round_completed", "round": 3, "ideas_added": 18, "coverage_delta": 0.07}
{"ts": "...", "type": "agent_started", "agent": "div_2", "task": "..."}
{"ts": "...", "type": "agent_completed", "agent": "div_2", "ideas_produced": 4}
{"ts": "...", "type": "phase_transition", "from": "divergent", "to": "clustering"}
{"ts": "...", "type": "axes_transformed", "old": ["mech","user"], "new": ["mech","horizon","ethics"]}
{"ts": "...", "type": "tournament_result", "winner": "i_0042", "loser": "i_0050", "judge_persona": "futurist-skeptic", "elo_delta": 14}
{"ts": "...", "type": "clusters_updated", "count": 6, "labels": ["thermal","electro","social","grid","wood","other"]}
{"ts": "...", "type": "pareto_extracted", "count": 9}
{"ts": "...", "type": "final_report"}
```

## `axes.json`
Morphological decomposition. Defines the MAP-Elites grid.

```json
{
  "version": 1,
  "axes": [
    {"name": "mechanism", "values": ["physical","social","digital","economic","biological"]},
    {"name": "user", "values": ["consumer","enterprise","gov","developer","community"]},
    {"name": "horizon", "values": ["year","decade","century"]}
  ],
  "rationale": "Mechanism is the dominant variation. User and horizon are orthogonal to mechanism and to each other.",
  "transformed_from": null
}
```

Subsequent transformations: `transformed_from` references the previous version id, archive copies preserved as `archive_v1.json` etc.

## `personas.json`

```json
{
  "personas": [
    {
      "id": "p_1",
      "name": "Maria Oliveira",
      "profession": "civil engineer specializing in retrofits",
      "age": 47,
      "culture": "Brazilian, lives in Curitiba",
      "cognitive_style": "concrete-detail-oriented, skeptical of buzzwords",
      "blind_spot": "tends to dismiss software-first solutions",
      "bias_vector": ["practical", "cost-sensitive", "retrofittable"],
      "interview": [
        {"q": "What's the first thing you check on a new project?", "a": "Whether the existing structure can handle the loads — most exciting designs ignore that."},
        ...
      ]
    }
  ]
}
```

## `archive.json` — MAP-Elites

```json
{
  "axes_version": 1,
  "dims": [8, 8],
  "cells": {
    "0,0": {"idea_id": "i_0012", "score": 0.78, "filled_at": "..."},
    "0,1": null
  },
  "coverage": 0.42,
  "transformations": []
}
```

Cell key is comma-separated index tuple matching `axes_version` order.

## `clusters.json`

```json
{
  "method": "hdbscan",
  "params": {"min_cluster_size": 3},
  "clusters": [
    {"id": 0, "label": "thermal-storage", "members": ["i_0042", "i_0019"], "centroid_id": "i_0042"}
  ],
  "noise": ["i_0001"]
}
```

## `elo.json`

```json
{
  "ratings": {"i_0042": 1620, "i_0050": 1486},
  "history": [
    {"round": 3, "judge_persona": "futurist-skeptic", "winner": "i_0042", "loser": "i_0050", "delta": 14}
  ]
}
```

## `pareto.json`

```json
{
  "axes": ["novelty", "feasibility", "impact"],
  "front": [
    {"id": "i_0042", "scores": [0.72, 0.61, 0.83]}
  ],
  "knee_point": "i_0042"
}
```

## `problem.json` — Socratic output

```json
{
  "original_topic": "energy storage residential",
  "refined_problem": "How can homes economically time-shift kWh between day and night without lithium grid batteries?",
  "how_might_we": [
    "How might we make residential thermal storage attractive without rebates?",
    ...
  ],
  "constraints": ["budget < $5k", "no rooftop modifications", "must be reversible"],
  "out_of_scope": ["utility-scale storage", "EV vehicle-to-grid"]
}
```
