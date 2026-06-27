"""HDBSCAN clustering over idea embeddings.

HDBSCAN is lazy-imported so that the lightweight tools (`health`, `archive_init`)
do not pay its startup cost.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


def cluster_embeddings(
    embeddings: Dict[str, List[float]],
    min_cluster_size: int = 3,
) -> Dict[str, object]:
    """Cluster a dict of ``{idea_id: vector}`` with HDBSCAN.

    Returns ``{"clusters": [{"id", "members", "centroid_id"}], "noise": [ids]}``.
    Cluster ID -1 (HDBSCAN noise) is reported under ``noise``.
    The centroid_id is the member whose vector is closest (cosine) to the
    cluster centroid.
    """
    if not embeddings:
        return {"clusters": [], "noise": []}

    ids = list(embeddings.keys())
    mat = np.asarray([embeddings[i] for i in ids], dtype=np.float32)

    # HDBSCAN needs at least min_cluster_size points to find a real cluster.
    if mat.shape[0] < max(2, min_cluster_size):
        return {"clusters": [], "noise": ids}

    # Lazy import so callers that only want bookkeeping aren't forced to install it.
    try:
        import hdbscan  # type: ignore
    except ImportError as exc:  # pragma: no cover
        logger.error("hdbscan not available: %s", exc)
        return {"clusters": [], "noise": ids, "error": "hdbscan_unavailable"}

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=int(min_cluster_size),
        metric="euclidean",
    )
    labels = clusterer.fit_predict(mat)

    clusters: List[Dict[str, object]] = []
    noise: List[str] = []
    unique = sorted(set(int(x) for x in labels))
    for label in unique:
        member_idx = [i for i, l in enumerate(labels) if int(l) == label]
        members = [ids[i] for i in member_idx]
        if label == -1:
            noise.extend(members)
            continue
        # Centroid in vector space, then pick nearest real member.
        sub = mat[member_idx]
        centroid = sub.mean(axis=0)
        # Cosine distance to centroid.
        sub_norm = np.linalg.norm(sub, axis=1)
        cen_norm = float(np.linalg.norm(centroid))
        if cen_norm == 0 or np.any(sub_norm == 0):
            # Fallback to euclidean.
            dists = np.linalg.norm(sub - centroid, axis=1)
            centroid_id = members[int(np.argmin(dists))]
        else:
            sims = (sub @ centroid) / (sub_norm * cen_norm + 1e-12)
            centroid_id = members[int(np.argmax(sims))]
        clusters.append(
            {
                "id": int(label),
                "members": members,
                "centroid_id": centroid_id,
            }
        )

    return {"clusters": clusters, "noise": noise}
