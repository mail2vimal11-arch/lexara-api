"""
FAISS-powered in-memory semantic clause search.
The index is populated at startup from the DB and updated as clauses are added.
"""

from __future__ import annotations
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

_EMBEDDING_DIM = 384
_index = None
_clause_store: list[dict] = []   # parallel list to FAISS index: [{clause_id, clause_text, clause_type}]


def _get_index():
    """Lazy-init FAISS index."""
    global _index
    if _index is None:
        import faiss
        _index = faiss.IndexFlatL2(_EMBEDDING_DIM)
        logger.info("FAISS index initialized")
    return _index


def add_clause_to_index(clause_id: str, clause_text: str, clause_type: str) -> None:
    """
    Add a clause to the FAISS semantic search index.
    Called after DB insert so search stays in sync.
    """
    from app.nlp.embeddings import embed_text
    index = _get_index()
    vector = embed_text(clause_text).reshape(1, -1)
    index.add(vector)
    _clause_store.append({
        "clause_id": clause_id,
        "clause_text": clause_text,
        "clause_type": clause_type,
    })


def search_similar_clauses(query: str, k: int = 5) -> list[dict]:
    """
    Semantic search: return the k most similar clauses to the query string.
    Returns empty list if index is empty.
    """
    from app.nlp.embeddings import embed_text
    index = _get_index()
    if index.ntotal == 0:
        return []
    k = min(k, index.ntotal)
    q_vec = embed_text(query).reshape(1, -1)
    distances, indices = index.search(q_vec, k)
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if 0 <= idx < len(_clause_store):
            result = dict(_clause_store[idx])
            result["distance"] = float(dist)
            results.append(result)
    return results


def bootstrap_index_from_db(db) -> None:
    """
    Populate the FAISS index from all clauses in the database at startup.
    Call once during app lifespan startup.
    """
    from app.models.clause import SOWClause
    clauses = db.query(SOWClause).all()
    for c in clauses:
        try:
            add_clause_to_index(c.clause_id, c.clause_text, c.clause_type or "General")
        except Exception as e:
            logger.warning(f"Could not index clause {c.clause_id}: {e}")
    logger.info(f"FAISS index bootstrapped with {len(clauses)} clauses")
