"""Smoke test for brainstorm-tools.

Exercises the archive/Pareto code paths without spinning up the full MCP server
and without requiring sentence-transformers / hdbscan. Run with::

    python tests/smoke_test.py

from the package root. Prints results — no assertion framework.
"""

from __future__ import annotations

import os
import sys
import tempfile

import numpy as np

# Ensure the package is importable when run from the repo root.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from brainstorm_tools import archive as _archive  # noqa: E402
from brainstorm_tools import pareto as _pareto  # noqa: E402


def main() -> None:
    rng = np.random.default_rng(seed=42)

    with tempfile.TemporaryDirectory(prefix="brainstorm_smoke_") as run_dir:
        print(f"[smoke] run_dir = {run_dir}")

        # --- archive_init: 2 axes, 5x5 ---
        axes = [
            {
                "name": "audience",
                "values": ["kids", "teens", "adults", "seniors", "experts"],
            },
            {
                "name": "format",
                "values": ["text", "audio", "video", "interactive", "physical"],
            },
        ]
        dims = [5, 5]
        handle = _archive.init_archive(run_dir, axes, dims)
        print(
            f"[smoke] archive_init -> total_cells={handle.total_cells()} "
            f"coverage={handle.coverage():.3f} dims={handle.dims}"
        )

        # --- place 5 ideas with random embeddings/scores/descriptors ---
        decisions = []
        for i in range(5):
            idea_id = f"i_{i:04d}"
            embedding = rng.standard_normal(384).astype(float).tolist()
            descriptor = [int(rng.integers(0, 5)), int(rng.integers(0, 5))]
            score = float(rng.uniform(0, 1))
            decision = handle.place(idea_id, embedding, descriptor, score)
            decisions.append((idea_id, descriptor, round(score, 3), decision))
            print(
                f"[smoke] place {idea_id} at {descriptor} score={score:.3f}"
                f" -> {decision}"
            )

        # Place a 6th idea aiming at an existing cell to exercise replace/reject.
        target_cell = decisions[0][1]
        forced = handle.place(
            "i_dup", [0.0] * 384, target_cell, score=0.999
        )
        print(f"[smoke] forced placement at {target_cell} -> {forced}")

        # --- coverage ---
        print(
            f"[smoke] coverage -> coverage={handle.coverage():.3f} "
            f"filled={handle.filled_cells()}/{handle.total_cells()}"
        )

        # --- underfilled suggestions ---
        suggestions = handle.suggest_underfilled(k=3)
        print("[smoke] suggest_underfilled (k=3):")
        for s in suggestions:
            print(
                f"   cell={s['cell']} density={s['neighbor_density']:.3f} "
                f"meaning={s['meaning']}"
            )

        # --- gaps ---
        gaps = handle.gaps()
        print(f"[smoke] coverage_gaps -> {len(gaps)} components")
        for g in gaps[:3]:
            print(
                f"   size={g['size']} centroid={g['centroid']} "
                f"meaning={g['meaning']}"
            )

        # --- pareto on 5 score triples ---
        scores = {
            "i_0000": [0.9, 0.4, 0.6],
            "i_0001": [0.6, 0.9, 0.5],
            "i_0002": [0.7, 0.7, 0.8],   # likely knee
            "i_0003": [0.3, 0.3, 0.3],   # dominated
            "i_0004": [0.5, 0.8, 0.4],
        }
        pf = _pareto.pareto_front(scores, maximize=[True, True, True])
        print(
            f"[smoke] pareto_front -> front={pf['front']} "
            f"knee={pf['knee']} ideal={pf['ideal']} anti_ideal={pf['anti_ideal']}"
        )

        # --- verify persistence reload ---
        reloaded = _archive.ArchiveHandle.load(run_dir)
        assert reloaded is not None
        print(
            f"[smoke] reload -> coverage={reloaded.coverage():.3f} "
            f"filled={reloaded.filled_cells()}"
        )

        print("[smoke] OK")


if __name__ == "__main__":
    main()
