"""
Comprehensive procurement clause seed data.
Imports 120+ reference clauses from the reference_data package.
Run once at startup to populate the clause library with curated standard clauses.
"""

from sqlalchemy.orm import Session
from app.models.clause import SOWClause
from app.nlp.search import add_clause_to_index
from app.services.reference_data import ALL_REFERENCE_CLAUSES
import uuid

SEED_CLAUSES = ALL_REFERENCE_CLAUSES


def seed_clauses(db: Session) -> int:
    """
    Insert seed clauses if not already present. Returns count of clauses inserted.
    Only runs once — skips if standard clauses already exist in the DB.
    Re-seeds if new clauses have been added to the reference library.
    """
    existing = db.query(SOWClause).filter(SOWClause.is_standard == True).count()  # noqa
    if existing >= len(SEED_CLAUSES):
        return 0

    # Get existing clause texts to avoid duplicates
    existing_texts = set()
    if existing > 0:
        for row in db.query(SOWClause.clause_text).filter(SOWClause.is_standard == True).all():  # noqa
            existing_texts.add(row[0][:80])

    inserted = 0
    for data in SEED_CLAUSES:
        # Skip if this clause text already exists
        if data["clause_text"][:80] in existing_texts:
            continue

        clause_id = str(uuid.uuid4())
        clause = SOWClause(clause_id=clause_id, confidence_score=1.0, **data)
        db.add(clause)
        add_clause_to_index(clause_id, data["clause_text"], data["clause_type"])
        inserted += 1

    db.commit()
    return inserted
