"""
Procurement Tools router — /v1/procurement/
Three stateless, regex/NLP-powered endpoints requiring no LLM quota:
  POST /v1/procurement/lint        — Readability linter
  POST /v1/procurement/citations   — McGill Guide citation validator
  POST /v1/procurement/clauses     — Clause library search
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List

from app.services.linter_service import lint
from app.services.citation_service import citation_summary
from app.services.clause_service import search_clauses, list_categories, list_clauses

router = APIRouter()


def _auth(authorization: Optional[str]):
    """Reuse same auth pattern as contracts router."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")


# ── Models ────────────────────────────────────────────────────────────────────

class TextRequest(BaseModel):
    text: str


class ClauseSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None


# ── POST /v1/procurement/lint ─────────────────────────────────────────────────

@router.post("/lint")
async def lint_document(
    request: TextRequest,
    authorization: str = Header(None),
):
    """
    Run the Justice Canada Readability Linter against contract text.
    Flags legalese, passive voice, plural party terms, and gendered language.
    No LLM required — fully deterministic regex + spaCy.
    """
    _auth(authorization)
    if len(request.text) < 20:
        raise HTTPException(status_code=400, detail="Text too short")
    if len(request.text) > 100_000:
        raise HTTPException(status_code=400, detail="Text exceeds 100,000 character limit")

    results = lint(request.text)

    # Flatten into a summary-friendly shape
    total = sum(len(v) for v in results.values())
    return {
        "total_issues": total,
        "legalese": results["legalese"],
        "passive_voice": results["passive_voice"],
        "plural_parties": results["plural_parties"],
        "gendered_language": results["gendered_language"],
    }


# ── POST /v1/procurement/citations ───────────────────────────────────────────

@router.post("/citations")
async def validate_citations(
    request: TextRequest,
    authorization: str = Header(None),
):
    """
    Validate Canadian legal citations against McGill Guide (10th ed.).
    Covers statutes (RSC/SC/SO etc.), SOR/SI regulations, and case citations.
    """
    _auth(authorization)
    if len(request.text) < 20:
        raise HTTPException(status_code=400, detail="Text too short")

    summary = citation_summary(request.text)

    return {
        "total": summary["total"],
        "statutes": [
            {"raw": f.raw, "valid": f.valid, "warnings": f.warnings}
            for f in summary["statutes"]
        ],
        "regulations": [
            {"raw": f.raw, "valid": f.valid, "warnings": f.warnings}
            for f in summary["regulations"]
        ],
        "cases": [
            {"raw": f.raw, "valid": f.valid, "warnings": f.warnings}
            for f in summary["cases"]
        ],
    }


# ── POST /v1/procurement/clauses ──────────────────────────────────────────────

@router.post("/clauses")
async def get_clauses(
    request: ClauseSearchRequest,
    authorization: str = Header(None),
):
    """
    Search the SACC-style clause library.
    Pass a query string and optional category filter.
    """
    _auth(authorization)

    if request.query.strip():
        results = search_clauses(request.query, category=request.category)
    else:
        results = list_clauses(category=request.category)

    # Strip internal score field before returning
    clean = [{k: v for k, v in c.items() if k != "_score"} for c in results]
    return {
        "total": len(clean),
        "categories": list_categories(),
        "clauses": clean,
    }
