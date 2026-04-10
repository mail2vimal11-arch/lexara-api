"""
Automated clause learning pipeline.
Extracts, classifies, deduplicates, and stores SOW clauses from ingested tenders.
"""

from __future__ import annotations
import logging
import uuid

from sqlalchemy.orm import Session

from app.nlp.pipeline import extract_clauses, classify_clause, detect_risk, improve_clause
from app.nlp.embeddings import embed_text
from app.nlp.search import add_clause_to_index, search_similar_clauses
from app.models.clause import SOWClause
from app.models.tender import Tender

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.15   # L2 distance — lower = more similar; skip if very close duplicate


def learn_from_tender(db: Session, tender: Tender) -> list[dict]:
    """
    Extract and store SOW clauses from a tender's description.
    Deduplicates against existing FAISS index before storing.

    Returns list of newly learned clause dicts.
    """
    text = tender.description or ""
    if len(text) < 50:
        return []

    sentences = extract_clauses(text)
    learned = []

    for sentence in sentences:
        if len(sentence) < 30:
            continue

        clause_type = classify_clause(sentence)
        risk = detect_risk(sentence)

        # Deduplicate: skip if very similar clause already exists in index
        similar = search_similar_clauses(sentence, k=1)
        if similar and similar[0]["distance"] < SIMILARITY_THRESHOLD:
            logger.debug(f"Skipping near-duplicate clause: {sentence[:60]}")
            continue

        clause_id = str(uuid.uuid4())
        clause = SOWClause(
            clause_id=clause_id,
            tender_id=tender.id,
            source=tender.source,
            clause_text=sentence,
            clause_type=clause_type,
            jurisdiction="CA-ON" if tender.country in ("CA", "Canada", "") else tender.country,
            industry="",
            risk_level=risk,
            confidence_score=0.85 if clause_type != "General" else 0.4,
            is_standard=False,
        )
        db.add(clause)

        # Add to live FAISS index
        add_clause_to_index(clause_id, sentence, clause_type)

        learned.append({"clause_id": clause_id, "clause_type": clause_type, "text": sentence[:100]})

    logger.info(f"Learned {len(learned)} clauses from tender {tender.tender_id}")
    return learned
