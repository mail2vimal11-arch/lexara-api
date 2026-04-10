"""
Sentence embeddings using sentence-transformers.
Lazy-loaded to avoid slow startup on first request.
"""

from __future__ import annotations
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

_model = None
_MODEL_NAME = "all-MiniLM-L6-v2"  # 384-dim, fast, good quality


def _get_model():
    """Lazy-load the embedding model on first use."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(_MODEL_NAME)
            logger.info(f"Loaded embedding model: {_MODEL_NAME}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _model


def embed_text(text: str) -> np.ndarray:
    """
    Generate a 384-dimensional embedding vector for the given text.
    Returns a float32 numpy array.
    """
    model = _get_model()
    return model.encode(text, convert_to_numpy=True).astype("float32")


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
