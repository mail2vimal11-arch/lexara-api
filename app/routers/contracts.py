"""Contract analysis endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
import httpx
import json
import logging
from datetime import datetime
import uuid

from app.config import settings
from app.database.session import get_db
from app.services.llm_service import analyze_with_claude

logger = logging.getLogger(__name__)
router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request body for contract analysis."""
    text: str
    contract_type: Optional[str] = "auto"  # "service_agreement", "nda", "employment", etc.
    jurisdiction: Optional[str] = "ON"
    doc_type: Optional[str] = "contract"
    include_recommendations: Optional[bool] = True


class RiskFlag(BaseModel):
    """Risk flag in analysis."""
    severity: str  # "critical", "high", "medium", "low"
    title: str
    description: str
    section: Optional[str] = None
    recommendation: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Response from contract analysis."""
    analysis_id: str
    backend: str
    summary: str
    confidence: float
    tokens_used: int
    risk_score: Optional[int] = None
    key_risks: Optional[List[RiskFlag]] = None
    missing_clauses: Optional[List[str]] = None
    processing_time_ms: int
    cost_cents: float


@router.post("/analyze-contract", response_model=AnalyzeResponse)
async def analyze_contract(
    request: AnalyzeRequest,
    authorization: str = Header(None),
    db = Depends(get_db)
):
    """
    Analyze a contract for legal risks.
    
    Returns:
    - Risk score (0-100)
    - Key risks with severity levels
    - Missing protective clauses
    - Actionable recommendations
    """
    
    start_time = datetime.utcnow()
    
    # Validate text length
    if len(request.text) < 100:
        raise HTTPException(
            status_code=400,
            detail="Contract text must be at least 100 characters"
        )
    if len(request.text) > 50000:
        raise HTTPException(
            status_code=400,
            detail="Contract text exceeds 50,000 characters. Please split into multiple documents."
        )
    
    # Validate API key
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    try:
        # Call Claude for analysis
        result = await analyze_with_claude(
            text=request.text,
            contract_type=request.contract_type,
            jurisdiction=request.jurisdiction,
            include_recommendations=request.include_recommendations
        )
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return AnalyzeResponse(
            analysis_id=f"anal_{uuid.uuid4().hex[:12]}",
            backend="claude",
            summary=result.get("summary", ""),
            confidence=result.get("confidence", 0.9),
            tokens_used=result.get("tokens_used", 0),
            risk_score=result.get("risk_score"),
            key_risks=result.get("key_risks", []),
            missing_clauses=result.get("missing_clauses", []),
            processing_time_ms=processing_time,
            cost_cents=3
        )
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Contract analysis failed. Please try again."
        )


@router.post("/extract-clauses")
async def extract_clauses(
    request: dict,
    authorization: str = Header(None)
):
    """
    Extract specific clauses from a contract.
    
    Supports:
    - liability
    - termination
    - confidentiality
    - indemnification
    - warranty
    - intellectual_property
    """
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    text = request.get("text", "")
    clause_types = request.get("clause_types", [])
    
    if not text or len(text) < 100:
        raise HTTPException(status_code=400, detail="Text is required and must be at least 100 characters")
    
    try:
        result = await analyze_with_claude(
            text=text,
            mode="extract_clauses",
            clause_types=clause_types
        )
        
        return {
            "analysis_id": f"anal_{uuid.uuid4().hex[:12]}",
            "clauses": result.get("clauses", []),
            "tokens_used": result.get("tokens_used", 0)
        }
    
    except Exception as e:
        logger.error(f"Clause extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Clause extraction failed")


@router.post("/risk-score")
async def calculate_risk_score(
    request: dict,
    authorization: str = Header(None)
):
    """
    Calculate quantified risk score (0-100) for a contract.
    
    Weighting factors:
    - liability: 0.25
    - data_protection: 0.30
    - termination: 0.15
    - ip_ownership: 0.20
    - warranty: 0.10
    """
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    text = request.get("text", "")
    weighting = request.get("weighting", {})
    
    if not text or len(text) < 100:
        raise HTTPException(status_code=400, detail="Text is required")
    
    try:
        result = await analyze_with_claude(
            text=text,
            mode="risk_score",
            weighting=weighting
        )
        
        return {
            "overall_risk_score": result.get("overall_risk_score", 50),
            "risk_level": result.get("risk_level", "medium"),
            "scores_by_category": result.get("scores_by_category", {}),
            "interpretation": result.get("interpretation", ""),
            "tokens_used": result.get("tokens_used", 0)
        }
    
    except Exception as e:
        logger.error(f"Risk scoring failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Risk scoring failed")
