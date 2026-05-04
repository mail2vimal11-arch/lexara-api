"""Contract analysis endpoints - tab-based approach."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from datetime import datetime
import uuid

from app.database.session import get_db
from app.services.llm_service import analyze_with_claude
from app.services.audit_service import log_action
from app.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Shared request model ──────────────────────────────────────────────────────

class ContractRequest(BaseModel):
    text: str
    contract_type: Optional[str] = "auto"
    jurisdiction: Optional[str] = "ON"


def _validate_text(request: ContractRequest):
    if len(request.text) < 100:
        raise HTTPException(status_code=400, detail="Contract text must be at least 100 characters")
    if len(request.text) > 50000:
        raise HTTPException(status_code=400, detail="Contract text exceeds 50,000 character limit")


# ── Tab 1: Summary ────────────────────────────────────────────────────────────

class SummaryResponse(BaseModel):
    analysis_id: str
    summary: str
    contract_type: str
    jurisdiction: str
    confidence: float
    tokens_used: int
    processing_time_ms: int


@router.post("/summary", response_model=SummaryResponse)
async def get_summary(
    request: ContractRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Tab 1 — Plain-English summary of the contract.
    Fast, cheap, ~500 tokens.
    """
    _validate_text(request)
    start = datetime.utcnow()
    try:
        result = await analyze_with_claude(
            text=request.text,
            contract_type=request.contract_type,
            jurisdiction=request.jurisdiction,
            mode="summary"
        )
        ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        aid = f"anal_{uuid.uuid4().hex[:12]}"
        log_action(db, "CONTRACT_SUMMARY",
                   {"analysis_id": aid, "tokens": result.get("tokens_used", 0), "ms": ms},
                   user_id=str(current_user.id))
        return SummaryResponse(
            analysis_id=aid,
            summary=result.get("summary", ""),
            contract_type=result.get("contract_type", request.contract_type),
            jurisdiction=result.get("jurisdiction", request.jurisdiction),
            confidence=result.get("confidence", 0.9),
            tokens_used=result.get("tokens_used", 0),
            processing_time_ms=ms
        )
    except Exception as e:
        logger.error(f"Summary failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Summary generation failed")


# ── Tab 2: Risk Score ─────────────────────────────────────────────────────────

class RiskScoreResponse(BaseModel):
    analysis_id: str
    overall_risk_score: int
    risk_level: str
    scores_by_category: dict
    interpretation: str
    tokens_used: int
    processing_time_ms: int


@router.post("/risk-score", response_model=RiskScoreResponse)
async def get_risk_score(
    request: ContractRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Tab 2 — Quantified risk score 0–100 with category breakdown.
    Categories: liability, data_protection, termination, ip_ownership, warranty.
    """
    _validate_text(request)
    start = datetime.utcnow()
    try:
        result = await analyze_with_claude(
            text=request.text,
            contract_type=request.contract_type,
            jurisdiction=request.jurisdiction,
            mode="risk_score"
        )
        ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        aid = f"anal_{uuid.uuid4().hex[:12]}"
        log_action(db, "CONTRACT_RISK_SCORE",
                   {"analysis_id": aid, "score": result.get("overall_risk_score"), "ms": ms},
                   user_id=str(current_user.id))
        return RiskScoreResponse(
            analysis_id=aid,
            overall_risk_score=result.get("overall_risk_score", 50),
            risk_level=result.get("risk_level", "medium"),
            scores_by_category=result.get("scores_by_category", {}),
            interpretation=result.get("interpretation", ""),
            tokens_used=result.get("tokens_used", 0),
            processing_time_ms=ms
        )
    except Exception as e:
        logger.error(f"Risk score failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Risk scoring failed")


# ── Tab 3: Key Risks ──────────────────────────────────────────────────────────

class RiskFlag(BaseModel):
    severity: str
    title: str
    description: str
    section: Optional[str] = None
    recommendation: Optional[str] = None


class KeyRisksResponse(BaseModel):
    analysis_id: str
    key_risks: List[RiskFlag]
    tokens_used: int
    processing_time_ms: int


@router.post("/key-risks", response_model=KeyRisksResponse)
async def get_key_risks(
    request: ContractRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Tab 3 — Detailed list of legal risks with severity and recommendations.
    Severities: critical, high, medium, low.
    """
    _validate_text(request)
    start = datetime.utcnow()
    try:
        result = await analyze_with_claude(
            text=request.text,
            contract_type=request.contract_type,
            jurisdiction=request.jurisdiction,
            mode="key_risks"
        )
        ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        aid = f"anal_{uuid.uuid4().hex[:12]}"
        log_action(db, "CONTRACT_KEY_RISKS",
                   {"analysis_id": aid, "count": len(result.get("key_risks", [])), "ms": ms},
                   user_id=str(current_user.id))
        return KeyRisksResponse(
            analysis_id=aid,
            key_risks=result.get("key_risks", []),
            tokens_used=result.get("tokens_used", 0),
            processing_time_ms=ms
        )
    except Exception as e:
        logger.error(f"Key risks failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Key risk analysis failed")


# ── Tab 4: Missing Clauses ────────────────────────────────────────────────────

class MissingClause(BaseModel):
    clause: str
    importance: str
    rationale: str


class MissingClausesResponse(BaseModel):
    analysis_id: str
    missing_clauses: List[MissingClause]
    tokens_used: int
    processing_time_ms: int


@router.post("/missing-clauses", response_model=MissingClausesResponse)
async def get_missing_clauses(
    request: ContractRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Tab 4 — Clauses that are absent but should be present.
    Importance: critical, high, medium, low.
    """
    _validate_text(request)
    start = datetime.utcnow()
    try:
        result = await analyze_with_claude(
            text=request.text,
            contract_type=request.contract_type,
            jurisdiction=request.jurisdiction,
            mode="missing_clauses"
        )
        ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        aid = f"anal_{uuid.uuid4().hex[:12]}"
        log_action(db, "CONTRACT_MISSING_CLAUSES",
                   {"analysis_id": aid, "count": len(result.get("missing_clauses", [])), "ms": ms},
                   user_id=str(current_user.id))
        return MissingClausesResponse(
            analysis_id=aid,
            missing_clauses=result.get("missing_clauses", []),
            tokens_used=result.get("tokens_used", 0),
            processing_time_ms=ms
        )
    except Exception as e:
        logger.error(f"Missing clauses failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Missing clause analysis failed")


# ── Tab 5: Extract Clauses ────────────────────────────────────────────────────

class ExtractedClause(BaseModel):
    type: str
    severity: str
    original: str
    revised: str
    rationale: str
    section: Optional[str] = None


class ExtractClausesResponse(BaseModel):
    analysis_id: str
    clauses: List[ExtractedClause]
    tokens_used: int
    processing_time_ms: int


@router.post("/extract-clauses", response_model=ExtractClausesResponse)
async def extract_clauses(
    request: ContractRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Tab 5 — Extract and categorize existing clauses.
    Types: liability, termination, confidentiality, indemnification, warranty, ip.
    """
    _validate_text(request)
    start = datetime.utcnow()
    try:
        result = await analyze_with_claude(
            text=request.text,
            contract_type=request.contract_type,
            jurisdiction=request.jurisdiction,
            mode="extract_clauses"
        )
        ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        aid = f"anal_{uuid.uuid4().hex[:12]}"
        log_action(db, "CONTRACT_EXTRACT_CLAUSES",
                   {"analysis_id": aid, "count": len(result.get("clauses", [])), "ms": ms},
                   user_id=str(current_user.id))
        return ExtractClausesResponse(
            analysis_id=aid,
            clauses=result.get("clauses", []),
            tokens_used=result.get("tokens_used", 0),
            processing_time_ms=ms
        )
    except Exception as e:
        logger.error(f"Clause extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Clause extraction failed")
