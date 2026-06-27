"""Lazy-loaded sentence-transformers embedding helpers.

The sentence-transformers model is heavy (downloads weights on first use), so we
defer the import and instantiation until the first call to ``get_model``.
"""

from __future__ import annotations

import logging
import threading
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Default 384-dim model.
MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_DIM = 384

# Module-level cache so the model is loaded only once per process.
_model = None
_model_lock = threading.Lock()


def get_model():
    """Return the (lazy) sentence-transformers model singleton."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        # Lazy import: sentence-transformers pulls in torch, which is huge.
        logger.info("Loading sentence-transformers model: %s", MODEL_NAME)
        from sentence_transformers import SentenceTransformer  # type: ignore

        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Model loaded.")
        return _model


def embed_one(text: str) -> List[float]:
    """Embed a single string as a list[float] of length EMBED_DIM."""
    model = get_model()
    vec = model.encode(text, normalize_embeddings=False)
    arr = np.asarray(vec, dtype=np.float32).reshape(-1)
    return arr.tolist()


def embed_many(texts: List[str]) -> List[List[float]]:
    """Embed a batch of strings, returning a list of vectors."""
    model = get_model()
    if not texts:
        return []
    vecs = model.encode(list(texts), normalize_embeddings=False, batch_size=32)
    arr = np.asarray(vecs, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr.tolist()


def cosine_matrix(vectors: List[List[float]]) -> List[List[float]]:
    """Compute the NxN cosine similarity matrix for a list of vectors.

    Robust to zero vectors (returns 0 for those rows/cols).
    """
    if not vectors:
        return []
    mat = np.asarray(vectors, dtype=np.float32)
    if mat.ndim == 1:
        mat = mat.reshape(1, -1)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    # Avoid division-by-zero for null vectors.
    safe_norms = np.where(norms == 0, 1.0, norms)
    normed = mat / safe_norms
    sim = normed @ normed.T
    # Zero out rows/cols where the original norm was 0.
    zero_mask = (norms.flatten() == 0)
    if zero_mask.any():
        sim[zero_mask, :] = 0.0
        sim[:, zero_mask] = 0.0
    # Clamp for numerical safety.
    sim = np.clip(sim, -1.0, 1.0)
    return sim.astype(float).tolist()


def cosine_one(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    av = np.asarray(a, dtype=np.float32)
    bv = np.asarray(b, dtype=np.float32)
    na = float(np.linalg.norm(av))
    nb = float(np.linalg.norm(bv))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.clip(np.dot(av, bv) / (na * nb), -1.0, 1.0))
