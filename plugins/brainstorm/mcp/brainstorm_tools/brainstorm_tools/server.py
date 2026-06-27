"""FastMCP server exposing Quality-Diversity bookkeeping + semantic ops.

The server is the glue layer that the ``claude-brainstorm-multiagent`` plugin
calls. The Claude orchestrator handles all LLM reasoning; this process never
makes LLM API calls.

Tools fall into three families:

* **Embedding / similarity** — ``embed``, ``embed_batch``, ``cosine_pairs``.
* **MAP-Elites archive** — ``archive_init``, ``archive_place``,
  ``archive_coverage``, ``archive_suggest_underfilled``, ``coverage_gaps``.
* **Analysis** — ``cluster_all``, ``pareto_front``, ``descriptor_from_text``.

Heavy dependencies (``sentence-transformers``, ``hdbscan``) are imported lazily
so that lightweight tools (``health``, ``archive_init``) start instantly.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Route logs to stderr — MCP servers reserve stdout for protocol.
logging.basicConfig(
    stream=sys.stderr,
    level=os.environ.get("BRAINSTORM_TOOLS_LOG", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("brainstorm_tools")

# FastMCP — modern MCP Python SDK.
try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except ImportError:  # pragma: no cover
    from fastmcp import FastMCP  # type: ignore  # older standalone package

from . import archive as _archive
from . import cluster as _cluster
from . import pareto as _pareto


VERSION = "0.1.0"

mcp = FastMCP("brainstorm-tools")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@mcp.tool()
def health() -> Dict[str, Any]:
    """Liveness check.

    Returns ``{"status": "ok", "version": "0.1.0"}``. Does not load any heavy
    dependencies — safe to call before models are warmed.
    """
    return {"status": "ok", "version": VERSION}


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

@mcp.tool()
def embed(text: str) -> List[float]:
    """Embed a single string with sentence-transformers ``all-MiniLM-L6-v2``.

    Returns a 384-dimensional float vector. The model is lazy-loaded on first
    call (~50MB download the first time, then cached).
    """
    from . import embed as _embed
    return _embed.embed_one(text)


@mcp.tool()
def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed many strings in one call. Returns an ``N x 384`` matrix.

    Faster than calling ``embed`` in a loop because sentence-transformers
    batches internally.
    """
    from . import embed as _embed
    return _embed.embed_many(texts)


@mcp.tool()
def cosine_pairs(vectors: List[List[float]]) -> List[List[float]]:
    """Compute the NxN cosine similarity matrix for the given vectors.

    Robust to zero-length vectors (rows/cols are zeroed out for those).
    Output is clamped to ``[-1, 1]`` for numerical safety.
    """
    from . import embed as _embed
    return _embed.cosine_matrix(vectors)


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

@mcp.tool()
def archive_init(
    run_dir: str,
    axes: List[Dict[str, Any]],
    dims: List[int],
) -> Dict[str, Any]:
    """Initialize a fresh MAP-Elites archive at ``<run_dir>/state/archive.json``.

    Each axis is a dict, either discrete (``{"name": ..., "values": [...]}``) or
    continuous-binned (``{"name": ..., "min": x, "max": y, "bins": N}``). The
    ``dims`` list is used as a fallback when an axis does not declare its own
    cardinality.

    The archive is overwritten if one already exists at this path. Also keeps
    an in-memory pyribs ``GridArchive`` keyed by ``run_dir`` for fast access.

    Returns the archive's summary view.
    """
    handle = _archive.init_archive(run_dir, axes, dims)
    return {
        "run_dir": run_dir,
        "dims": handle.dims,
        "total_cells": handle.total_cells(),
        "coverage": handle.coverage(),
        "path": os.path.join(run_dir, "state", "archive.json"),
    }


@mcp.tool()
def archive_place(
    run_dir: str,
    idea_id: str,
    embedding: List[float],
    descriptor: List[int],
    score: float,
) -> Dict[str, Any]:
    """Place an idea into its descriptor cell using MAP-Elites elitist rules.

    Behavior:

    * **new** — cell was empty; idea moves in.
    * **replaced** — cell was occupied but the new score beats the incumbent;
      the displaced idea_id is returned.
    * **rejected_dominated** — incumbent's score is >= new score; archive
      unchanged.

    Returns ``{"decision", "cell", "displaced"}``. Persists the update to
    ``archive.json`` atomically (write-then-rename).

    Raises if no archive has been initialized for this ``run_dir``.
    """
    handle = _archive.get_or_load(run_dir)
    if handle is None:
        raise ValueError(
            f"No archive initialized for run_dir={run_dir!r}. "
            "Call archive_init first."
        )
    return handle.place(idea_id, embedding, descriptor, score)


@mcp.tool()
def archive_coverage(run_dir: str) -> Dict[str, Any]:
    """Report coverage of the MAP-Elites archive.

    Returns ``{"coverage": 0..1, "filled_cells": N, "total_cells": M}``.
    Returns zeros if the archive is missing or unreadable.
    """
    handle = _archive.get_or_load(run_dir)
    if handle is None:
        return {"coverage": 0.0, "filled_cells": 0, "total_cells": 0}
    return {
        "coverage": handle.coverage(),
        "filled_cells": handle.filled_cells(),
        "total_cells": handle.total_cells(),
    }


@mcp.tool()
def archive_suggest_underfilled(
    run_dir: str,
    k: int = 3,
) -> List[Dict[str, Any]]:
    """Return ``k`` cells whose Chebyshev-radius-1 neighborhood is least filled.

    Uses *neighbor density*, not just empty/filled, so the orchestrator gets a
    smooth signal of where the archive is sparse rather than oscillating
    between isolated empty cells. Each suggestion includes:

    * ``cell`` — integer coordinates.
    * ``meaning`` — ``{axis_name: human_value}`` derived from the axes spec.
    * ``neighbor_density`` — fraction of neighbors (including self) that are
      occupied, in ``[0, 1]``.
    """
    handle = _archive.get_or_load(run_dir)
    if handle is None:
        return []
    return handle.suggest_underfilled(k=int(k))


@mcp.tool()
def coverage_gaps(run_dir: str) -> List[Dict[str, Any]]:
    """Return the connected components of empty cells, largest first.

    This is a higher-level companion to ``archive_suggest_underfilled``: where
    that returns individual sparse cells, this returns *structural* gaps —
    contiguous empty regions in the MAP-Elites grid. Each gap reports:

    * ``size`` — number of empty cells in the component.
    * ``centroid`` — center cell of the component, with ``meaning`` translated
      via the axes spec.
    * ``bounding_box`` — ``{"min": [...], "max": [...]}`` of the component.
    * ``members`` — list of all cells inside the gap.

    Useful for prompting Claude with "this whole region of the design space is
    unexplored" rather than just "this one cell is empty".
    """
    handle = _archive.get_or_load(run_dir)
    if handle is None:
        return []
    return handle.gaps()


# ---------------------------------------------------------------------------
# Clustering & Pareto
# ---------------------------------------------------------------------------

@mcp.tool()
def cluster_all(
    run_dir: str,
    embeddings: Dict[str, List[float]],
    min_cluster_size: int = 3,
) -> Dict[str, Any]:
    """Cluster the provided embeddings with HDBSCAN.

    ``embeddings`` is a dict ``{idea_id: vector}``. Returns
    ``{"clusters": [{"id", "members", "centroid_id"}], "noise": [ids]}``. The
    centroid_id is the member whose vector is closest (cosine) to the cluster
    centroid — i.e. the most representative idea.

    The ``run_dir`` parameter is accepted but currently unused (reserved for
    future per-run caching / archive-aware clustering).
    """
    del run_dir  # reserved
    return _cluster.cluster_embeddings(
        embeddings, min_cluster_size=int(min_cluster_size)
    )


@mcp.tool()
def pareto_front(
    scores: Dict[str, List[float]],
    maximize: Optional[List[bool]] = None,
) -> Dict[str, Any]:
    """Compute the Pareto front + knee point for multi-objective scores.

    ``scores`` is ``{idea_id: [s1, s2, ...]}``, typically ``[novelty,
    feasibility, impact]``. ``maximize`` is a per-axis flag (defaults to all
    True).

    Returns ``{"front": [ids], "knee": id_or_None, "ideal": [...],
    "anti_ideal": [...]}``. The knee uses the minimum normalized distance to
    the utopian (ideal) corner of the score space — a standard heuristic for
    picking the "most balanced" non-dominated solution.
    """
    return _pareto.pareto_front(scores, maximize=maximize)


# ---------------------------------------------------------------------------
# Heuristic descriptor inference
# ---------------------------------------------------------------------------

@mcp.tool()
def descriptor_from_text(
    text: str,
    axes: List[Dict[str, Any]],
) -> List[int]:
    """Heuristically infer the MAP-Elites cell coordinates for free-form text.

    For each axis, we embed every possible value's label and pick the index
    whose embedding is closest (cosine) to the input text's embedding.

    **CAVEAT — this is a heuristic.** Quality depends on how descriptive the
    axis-value labels are. For nuanced descriptors prefer to have Claude
    classify the text explicitly, or use this as a first-pass hint. Continuous
    axes (``min``/``max``/``bins``) fall through to bin index 0 unless they
    declare ``values`` for each bin; supply explicit labels if you want them
    inferred from text.
    """
    from . import embed as _embed

    text_vec = _embed.embed_one(text)

    coords: List[int] = []
    for axis in axes:
        values = axis.get("values")
        if not values:
            # No labels to compare against — heuristic isn't applicable.
            coords.append(0)
            continue
        # Embed each label, picking argmax cosine sim with the text.
        labels = [str(v) for v in values]
        label_vecs = _embed.embed_many(labels)
        sims = [_embed.cosine_one(text_vec, lv) for lv in label_vecs]
        coords.append(int(max(range(len(sims)), key=lambda i: sims[i])))
    return coords


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Console-script entry point: ``brainstorm-tools``.

    Runs the FastMCP server over stdio (default MCP transport).
    """
    logger.info("Starting brainstorm-tools MCP server v%s", VERSION)
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
