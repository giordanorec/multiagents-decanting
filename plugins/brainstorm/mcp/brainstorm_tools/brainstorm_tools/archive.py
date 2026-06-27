"""MAP-Elites archive bookkeeping with JSON persistence.

We keep two things in sync:

* An in-memory pyribs ``GridArchive`` (keyed by ``run_dir``) used for fast cell
  lookups; pyribs is the canonical Quality-Diversity library.
* A custom JSON file at ``<run_dir>/state/archive.json`` that captures the full
  state in a portable, human-readable form. JSON is the source of truth for
  cross-run reloads since pyribs uses numpy types throughout, which don't
  round-trip through plain JSON.

Schema of ``archive.json``::

    {
      "axes_version": 1,
      "dims": [8, 8],
      "axes": [ {full axis def}, ... ],
      "cells": {
        "0,0": {"idea_id": "i_0012", "score": 0.78, "filled_at": "..."},
        "0,1": null,
        ...
      },
      "coverage": 0.42,
      "transformations": []
    }
"""

from __future__ import annotations

import datetime as _dt
import itertools
import json
import logging
import os
import tempfile
import threading
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# In-memory caches.
_archives: Dict[str, "ArchiveHandle"] = {}
_archives_lock = threading.RLock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cell_key(coords: List[int]) -> str:
    return ",".join(str(int(c)) for c in coords)


def _parse_cell_key(key: str) -> List[int]:
    return [int(p) for p in key.split(",")]


def _state_dir(run_dir: str) -> str:
    return os.path.join(run_dir, "state")


def _archive_path(run_dir: str) -> str:
    return os.path.join(_state_dir(run_dir), "archive.json")


def _atomic_write(path: str, data: str) -> None:
    """Write data to path atomically: write to .tmp in same dir, then os.replace."""
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".archive_", suffix=".tmp", dir=parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                # fsync may not be available on some Windows handles; non-fatal.
                pass
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _all_coords(dims: List[int]) -> List[Tuple[int, ...]]:
    return list(itertools.product(*[range(d) for d in dims]))


def _axis_value_at(axis: Dict[str, Any], idx: int) -> Any:
    """Return the human-readable label for index ``idx`` on the given axis.

    Supports two axis styles:

    * ``{"name": "...", "values": ["low","mid","high"]}`` — discrete labels.
    * ``{"name": "...", "min": 0, "max": 1, "bins": N}`` — continuous binned axis;
      we return the bin center.
    """
    if "values" in axis and axis["values"]:
        vals = list(axis["values"])
        if 0 <= idx < len(vals):
            return vals[idx]
        return idx
    if "min" in axis and "max" in axis and "bins" in axis:
        lo, hi, bins = float(axis["min"]), float(axis["max"]), int(axis["bins"])
        if bins <= 0:
            return idx
        width = (hi - lo) / bins
        return lo + (idx + 0.5) * width
    return idx


def _axis_dim(axis: Dict[str, Any], fallback: int) -> int:
    if "values" in axis and axis["values"]:
        return len(axis["values"])
    if "bins" in axis:
        return int(axis["bins"])
    return int(fallback)


# ---------------------------------------------------------------------------
# Archive handle
# ---------------------------------------------------------------------------

class ArchiveHandle:
    """In-memory + on-disk archive state for one run_dir."""

    def __init__(
        self,
        run_dir: str,
        axes: List[Dict[str, Any]],
        dims: List[int],
        cells: Optional[Dict[str, Optional[Dict[str, Any]]]] = None,
        transformations: Optional[List[Any]] = None,
        axes_version: int = 1,
    ):
        self.run_dir = run_dir
        self.axes = axes
        self.dims = list(dims)
        self.axes_version = axes_version
        self.transformations: List[Any] = list(transformations or [])
        self._lock = threading.RLock()

        # Initialize all-empty cells dict if not provided.
        if cells is None:
            cells = {_cell_key(list(c)): None for c in _all_coords(self.dims)}
        self.cells: Dict[str, Optional[Dict[str, Any]]] = cells

        # Lazy pyribs archive (built on demand to avoid mandatory dependency at init).
        self._ribs_archive = None

    # -- pyribs --------------------------------------------------------

    def _ensure_ribs(self):
        if self._ribs_archive is not None:
            return self._ribs_archive
        try:
            from ribs.archives import GridArchive  # type: ignore

            # We don't actually need a meaningful solution_dim for our use; pyribs
            # requires one but we only use the archive for cell bookkeeping. Use
            # the embedding dim (384) as a sensible default placeholder.
            ranges = [(0.0, float(d)) for d in self.dims]
            self._ribs_archive = GridArchive(
                solution_dim=384,
                dims=list(self.dims),
                ranges=ranges,
            )
        except Exception as exc:  # pragma: no cover - optional path
            logger.warning("pyribs unavailable, falling back to JSON-only: %s", exc)
            self._ribs_archive = None
        return self._ribs_archive

    # -- persistence ---------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "axes_version": self.axes_version,
            "dims": list(self.dims),
            "axes": self.axes,
            "cells": self.cells,
            "coverage": self.coverage(),
            "transformations": self.transformations,
        }

    def save(self) -> None:
        path = _archive_path(self.run_dir)
        data = json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        _atomic_write(path, data)

    @classmethod
    def load(cls, run_dir: str) -> Optional["ArchiveHandle"]:
        path = _archive_path(run_dir)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load archive at %s: %s", path, exc)
            return None
        return cls(
            run_dir=run_dir,
            axes=raw.get("axes", []),
            dims=raw.get("dims", []),
            cells=raw.get("cells", None),
            transformations=raw.get("transformations", []),
            axes_version=raw.get("axes_version", 1),
        )

    # -- queries -------------------------------------------------------

    def total_cells(self) -> int:
        total = 1
        for d in self.dims:
            total *= max(1, int(d))
        return total

    def filled_cells(self) -> int:
        return sum(1 for v in self.cells.values() if v is not None)

    def coverage(self) -> float:
        total = self.total_cells()
        if total == 0:
            return 0.0
        return self.filled_cells() / total

    def cell_meaning(self, coords: List[int]) -> Dict[str, Any]:
        meaning: Dict[str, Any] = {}
        for axis, idx in zip(self.axes, coords):
            name = axis.get("name", "axis")
            meaning[name] = _axis_value_at(axis, int(idx))
        return meaning

    # -- mutation ------------------------------------------------------

    def place(
        self,
        idea_id: str,
        embedding: List[float],
        descriptor: List[int],
        score: float,
    ) -> Dict[str, Any]:
        """Place an idea into its descriptor cell.

        Returns a decision dict ``{"decision", "cell", "displaced"}``.
        """
        with self._lock:
            if len(descriptor) != len(self.dims):
                raise ValueError(
                    f"descriptor length {len(descriptor)} != axes count {len(self.dims)}"
                )
            # Clamp coords into valid range — defensive against descriptor_from_text
            # heuristics returning out-of-range indices.
            coords = [
                max(0, min(int(d) - 1, int(c)))
                for c, d in zip(descriptor, self.dims)
            ]
            key = _cell_key(coords)
            existing = self.cells.get(key)

            displaced: Optional[str] = None
            if existing is None:
                decision = "new"
                self.cells[key] = {
                    "idea_id": idea_id,
                    "score": float(score),
                    "filled_at": _now_iso(),
                }
            else:
                # Higher score wins.
                if float(score) > float(existing.get("score", float("-inf"))):
                    displaced = existing.get("idea_id")
                    decision = "replaced"
                    self.cells[key] = {
                        "idea_id": idea_id,
                        "score": float(score),
                        "filled_at": _now_iso(),
                    }
                else:
                    decision = "rejected_dominated"

            # Best-effort mirror into pyribs (not load-bearing for persistence).
            ribs = self._ensure_ribs()
            if ribs is not None and decision in ("new", "replaced"):
                try:
                    # pyribs >= 0.7 uses .add with arrays.
                    sol = np.asarray(embedding, dtype=np.float32)
                    if sol.shape[0] != 384:
                        # Pad/truncate so the placeholder solution_dim matches.
                        out = np.zeros(384, dtype=np.float32)
                        n = min(384, sol.shape[0])
                        out[:n] = sol[:n]
                        sol = out
                    ribs.add_single(
                        solution=sol,
                        objective=float(score),
                        measures=np.asarray(coords, dtype=np.float32) + 0.5,
                    )
                except Exception as exc:  # pragma: no cover
                    logger.debug("pyribs add failed (non-fatal): %s", exc)

            self.save()
            return {
                "decision": decision,
                "cell": coords,
                "displaced": displaced,
            }

    # -- analysis ------------------------------------------------------

    def neighbor_density(self, coords: Tuple[int, ...], radius: int = 1) -> float:
        """Fraction of the (Chebyshev radius=1) neighborhood that is filled.

        Includes the cell itself. Out-of-range neighbors are skipped (denominator
        is the count of in-range neighbors, so corner cells aren't penalized).
        """
        neighbors = []
        for delta in itertools.product(range(-radius, radius + 1), repeat=len(self.dims)):
            nc = [coords[i] + delta[i] for i in range(len(self.dims))]
            if all(0 <= nc[i] < self.dims[i] for i in range(len(self.dims))):
                neighbors.append(tuple(nc))
        if not neighbors:
            return 0.0
        filled = 0
        for nc in neighbors:
            key = _cell_key(list(nc))
            if self.cells.get(key) is not None:
                filled += 1
        return filled / len(neighbors)

    def suggest_underfilled(self, k: int = 3) -> List[Dict[str, Any]]:
        """Return the k cells with the lowest neighborhood density.

        Ties are broken by preferring empty cells over filled ones.
        """
        scored: List[Tuple[float, int, Tuple[int, ...]]] = []
        for coords in _all_coords(self.dims):
            density = self.neighbor_density(coords)
            empty_bias = 0 if self.cells.get(_cell_key(list(coords))) is None else 1
            scored.append((density, empty_bias, coords))
        scored.sort(key=lambda t: (t[0], t[1]))
        out: List[Dict[str, Any]] = []
        for density, _, coords in scored[: max(0, int(k))]:
            out.append(
                {
                    "cell": list(coords),
                    "meaning": self.cell_meaning(list(coords)),
                    "neighbor_density": float(density),
                }
            )
        return out

    def gaps(self) -> List[Dict[str, Any]]:
        """Return connected components of empty cells (Chebyshev-adjacent).

        Each component carries the bounding box, sample-meaning of its centroid,
        and the list of member cell coords.
        """
        empty = {
            tuple(_parse_cell_key(k))
            for k, v in self.cells.items()
            if v is None
        }
        visited: set = set()
        components: List[List[Tuple[int, ...]]] = []

        def neighbors_of(c: Tuple[int, ...]):
            for delta in itertools.product([-1, 0, 1], repeat=len(self.dims)):
                if all(d == 0 for d in delta):
                    continue
                nc = tuple(c[i] + delta[i] for i in range(len(self.dims)))
                if nc in empty:
                    yield nc

        for cell in empty:
            if cell in visited:
                continue
            # BFS.
            stack = [cell]
            comp: List[Tuple[int, ...]] = []
            while stack:
                cur = stack.pop()
                if cur in visited:
                    continue
                visited.add(cur)
                comp.append(cur)
                for nb in neighbors_of(cur):
                    if nb not in visited:
                        stack.append(nb)
            components.append(comp)

        # Sort components by size, descending — biggest gaps first.
        components.sort(key=len, reverse=True)
        out: List[Dict[str, Any]] = []
        for comp in components:
            arr = np.asarray(comp, dtype=np.int32)
            centroid = arr.mean(axis=0).round().astype(int).tolist()
            # Clamp centroid into the grid.
            centroid = [
                max(0, min(self.dims[i] - 1, int(centroid[i])))
                for i in range(len(self.dims))
            ]
            mins = arr.min(axis=0).tolist()
            maxs = arr.max(axis=0).tolist()
            out.append(
                {
                    "size": len(comp),
                    "centroid": centroid,
                    "meaning": self.cell_meaning(centroid),
                    "bounding_box": {"min": mins, "max": maxs},
                    "members": [list(c) for c in comp],
                }
            )
        return out


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def get_or_load(run_dir: str) -> Optional[ArchiveHandle]:
    """Return the cached handle for ``run_dir``, loading from disk if needed."""
    with _archives_lock:
        h = _archives.get(run_dir)
        if h is not None:
            return h
        loaded = ArchiveHandle.load(run_dir)
        if loaded is not None:
            _archives[run_dir] = loaded
        return loaded


def register(handle: ArchiveHandle) -> None:
    with _archives_lock:
        _archives[handle.run_dir] = handle


def init_archive(
    run_dir: str,
    axes: List[Dict[str, Any]],
    dims: List[int],
) -> ArchiveHandle:
    """Create + persist a fresh archive (overwrites any prior state file)."""
    # Reconcile dims with axes if axes carry inherent dimensionality.
    resolved_dims: List[int] = []
    for i, axis in enumerate(axes):
        fallback = int(dims[i]) if i < len(dims) else 1
        resolved_dims.append(_axis_dim(axis, fallback))
    handle = ArchiveHandle(
        run_dir=run_dir,
        axes=axes,
        dims=resolved_dims,
    )
    handle.save()
    register(handle)
    return handle
