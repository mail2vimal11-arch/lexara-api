"""
Bid comparison stress-test endpoints — /v1/bid-comparison/

Routes:
    POST /v1/bid-comparison/stress-test    Run all scenario types across N competing
                                           vendor bids and return a comparison matrix.

This is Step 3 of the "Blast Radius" engine: extends the single-clause scenario
simulator to N-bid competitive comparisons over a shared scenario set.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.models.user import User
from app.security import get_current_user
from app.services.scenario_simulator import (
    KNOWN_SCENARIO_TYPES,
    simulate_bid_comparison,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/bid-comparison", tags=["bid-comparison"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ClauseInput(BaseModel):
    """One clause from a vendor's bid. Mirrors the shape simulate_scenario expects."""

    clause_key: str = Field(..., description="Stable identifier for this clause within the bid.")
    clause_type: str = Field(
        ...,
        description="One of: liability, termination, ip_ownership, payment_terms, sla, acceptance_criteria.",
    )
    risk_severity: str = Field("medium", description="critical | high | medium | low")
    original_text: Optional[str] = None
    your_proposed_text: Optional[str] = None


class BidInput(BaseModel):
    bid_id: str
    vendor_name: str
    clauses: list[ClauseInput]
    contract_value_cad: Optional[float] = None
    headline_price_cad: Optional[float] = None
    vendor_metadata: Optional[dict] = None

    @field_validator("clauses")
    @classmethod
    def _at_least_one_clause(cls, v: list[ClauseInput]) -> list[ClauseInput]:
        if not v or len(v) == 0:
            raise ValueError("each bid must include at least one clause")
        return v


class SessionInput(BaseModel):
    contract_value_cad: float = 1_000_000.0
    jurisdiction_code: str = "ON"


class BidStressTestRequest(BaseModel):
    bids: list[BidInput]
    session: SessionInput
    scenarios: Optional[list[str]] = None

    @field_validator("bids")
    @classmethod
    def _at_least_two_bids(cls, v: list[BidInput]) -> list[BidInput]:
        if len(v) < 2:
            raise ValueError("at least 2 bids are required for a comparison")
        return v

    @field_validator("scenarios")
    @classmethod
    def _known_scenarios(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        unknown = [s for s in v if s not in KNOWN_SCENARIO_TYPES]
        if unknown:
            raise ValueError(
                f"unknown scenario types: {unknown}. "
                f"Allowed: {list(KNOWN_SCENARIO_TYPES)}"
            )
        if len(v) == 0:
            raise ValueError("scenarios list, if provided, must not be empty")
        return v


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/stress-test")
async def stress_test_bids(
    payload: BidStressTestRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Run scenario stress-tests across N competing bids and return the comparison
    matrix (per-bid totals, dominant risks, ranking, head-to-head insights).
    """
    bids_payload = [b.model_dump() for b in payload.bids]
    session_payload = payload.session.model_dump()

    try:
        result = await simulate_bid_comparison(
            bids=bids_payload,
            session_data=session_payload,
            scenarios=payload.scenarios,
        )
    except Exception as e:
        logger.exception("Bid comparison stress-test failed")
        raise HTTPException(status_code=500, detail=f"stress-test failed: {e}")

    return result
