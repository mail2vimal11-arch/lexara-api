"""Clause analysis, search, and library routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.nlp.pipeline import analyze_clause, extract_clauses
from app.nlp.search import search_similar_clauses
from app.models.clause import SOWClause
from app.models.user import User
from app.security import get_current_user
from app.services.audit_service import log_action

router = APIRouter(prefix="/clauses", tags=["Clauses"])


class AnalyzeRequest(BaseModel):
    text: str


class SearchRequest(BaseModel):
    query: str
    k: int = 5
    clause_type: Optional[str] = None
    jurisdiction: Optional[str] = None


@router.post("/analyze")
def analyze(
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze a clause: classify, detect risk, and suggest improvements.
    Also returns semantically similar clauses from the library.
    """
    result = analyze_clause(req.text)
    similar = search_similar_clauses(req.text, k=3)
    result["similar_clauses"] = similar

    log_action(db, "CLAUSE_ANALYZED",
               {"text_preview": req.text[:100], "type": result["clause_type"], "risk": result["risk_level"]},
               user_id=current_user.id)
    return result


@router.post("/search")
def search(
    req: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantic search across the clause library.
    Optionally filter by clause_type or jurisdiction.
    """
    results = search_similar_clauses(req.query, k=req.k)

    # Post-filter by type/jurisdiction if requested
    if req.clause_type:
        results = [r for r in results if r.get("clause_type") == req.clause_type]

    # CA-012: batch-fetch all matched clause rows in one query instead of N+1 SELECTs
    result_ids   = [r["clause_id"] for r in results]
    distance_map = {r["clause_id"]: r.get("distance") for r in results}

    clause_rows = (
        db.query(SOWClause)
        .filter(SOWClause.clause_id.in_(result_ids))
        .all()
    )
    clause_map = {c.clause_id: c for c in clause_rows}

    enriched = []
    for cid in result_ids:
        clause = clause_map.get(cid)
        if clause:
            enriched.append({
                "clause_id": clause.clause_id,
                "clause_text": clause.clause_text,
                "clause_type": clause.clause_type,
                "jurisdiction": clause.jurisdiction,
                "risk_level": clause.risk_level,
                "is_standard": clause.is_standard,
                "similarity_distance": distance_map.get(cid),
            })

    log_action(db, "CLAUSE_SEARCH", {"query": req.query, "results": len(enriched)}, user_id=current_user.id)
    return {"total": len(enriched), "clauses": enriched}


@router.get("/library")
def library(
    clause_type: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    standard_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the clause library with optional filters."""
    q = db.query(SOWClause)
    if clause_type:
        q = q.filter(SOWClause.clause_type == clause_type)
    if jurisdiction:
        q = q.filter(SOWClause.jurisdiction == jurisdiction)
    if standard_only:
        q = q.filter(SOWClause.is_standard.is_(True))  # CA-028: use .is_(True) not == True
    clauses = q.order_by(SOWClause.is_standard.desc(), SOWClause.created_at.desc()).limit(100).all()

    return {
        "total": len(clauses),
        "clauses": [
            {
                "clause_id": c.clause_id,
                "clause_text": c.clause_text,
                "clause_type": c.clause_type,
                "subtype": c.subtype,
                "jurisdiction": c.jurisdiction,
                "industry": c.industry,
                "risk_level": c.risk_level,
                "is_standard": c.is_standard,
                "confidence_score": c.confidence_score,
            }
            for c in clauses
        ],
    }
