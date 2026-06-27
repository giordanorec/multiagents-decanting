"""Pareto-front computation with a knee-point selection heuristic."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np


def _dominates(a: np.ndarray, b: np.ndarray, maximize: np.ndarray) -> bool:
    """Return True iff a dominates b under the given maximize/minimize per-axis flags.

    Domination: a is at least as good as b on every axis, and strictly better on at
    least one axis.
    """
    # Convert minimize axes to "negated" comparisons so we can do all-max logic.
    sign = np.where(maximize, 1.0, -1.0)
    aa = a * sign
    bb = b * sign
    geq = np.all(aa >= bb)
    gt = np.any(aa > bb)
    return bool(geq and gt)


def pareto_front(
    scores: Dict[str, List[float]],
    maximize: Optional[List[bool]] = None,
) -> Dict[str, object]:
    """Return the non-dominated set plus a knee point.

    Args:
        scores: ``{idea_id: [s1, s2, ...]}`` — every list must have the same length.
        maximize: per-axis flag (True = bigger is better). Defaults to all True.

    Returns:
        ``{"front": [ids], "knee": id_or_None, "ideal": [...], "anti_ideal": [...]}``.
        The knee is the front point with minimum normalized distance to the "utopian"
        (ideal) corner, scaled by the range on each axis.
    """
    if not scores:
        return {"front": [], "knee": None, "ideal": [], "anti_ideal": []}

    ids = list(scores.keys())
    mat = np.asarray([scores[i] for i in ids], dtype=np.float64)
    n, d = mat.shape

    if maximize is None:
        maximize_arr = np.ones(d, dtype=bool)
    else:
        if len(maximize) != d:
            raise ValueError(
                f"maximize length {len(maximize)} != score dim {d}"
            )
        maximize_arr = np.asarray(maximize, dtype=bool)

    # Find non-dominated set via O(n^2) check (n is small for brainstorming runs).
    dominated = np.zeros(n, dtype=bool)
    for i in range(n):
        if dominated[i]:
            continue
        for j in range(n):
            if i == j or dominated[j]:
                continue
            if _dominates(mat[j], mat[i], maximize_arr):
                dominated[i] = True
                break

    front_idx = [i for i in range(n) if not dominated[i]]
    front_ids = [ids[i] for i in front_idx]

    # Ideal / anti-ideal across the *whole* set (better reference than just the front).
    ideal = np.where(maximize_arr, mat.max(axis=0), mat.min(axis=0))
    anti_ideal = np.where(maximize_arr, mat.min(axis=0), mat.max(axis=0))

    # Knee point: minimum normalized distance to ideal among front members.
    knee_id: Optional[str] = None
    if front_idx:
        ranges = np.where(
            (ideal - anti_ideal) == 0, 1.0, np.abs(ideal - anti_ideal)
        )
        front_mat = mat[front_idx]
        # Distance to ideal, normalized.
        diff = (ideal - front_mat) * np.where(maximize_arr, 1.0, -1.0)
        # For maximize: ideal - x is non-negative if x <= ideal (it is).
        # For minimize: we flipped sign so it's also non-negative.
        norm_diff = diff / ranges
        dists = np.linalg.norm(norm_diff, axis=1)
        knee_local = int(np.argmin(dists))
        knee_id = front_ids[knee_local]

    return {
        "front": front_ids,
        "knee": knee_id,
        "ideal": ideal.tolist(),
        "anti_ideal": anti_ideal.tolist(),
    }
