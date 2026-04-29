"""
Portfolio Obligation Index — /v1/portfolio

Step 1 of the Lexara "Blast Radius" engine. Lets a user catalogue every
contract in their portfolio and the obligations attached to each one.

This is the data foundation for cross-contract cascade detection:
deadlines, penalties, and liability caps are all stored in a uniform,
queryable shape so the future cascade detector can scan one user's
entire obligation graph in a single indexed query.

Routes:
    POST   /v1/portfolio/contracts
    GET    /v1/portfolio/contracts
    GET    /v1/portfolio/contracts/{contract_id}
    PATCH  /v1/portfolio/contracts/{contract_id}
    DELETE /v1/portfolio/contracts/{contract_id}

    POST   /v1/portfolio/contracts/{contract_id}/obligations
    GET    /v1/portfolio/contracts/{contract_id}/obligations

    GET    /v1/portfolio/obligations
    PATCH  /v1/portfolio/obligations/{obligation_id}
    DELETE /v1/portfolio/obligations/{obligation_id}
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.obligation import Obligation
from app.models.portfolio_contract import PortfolioContract
from app.models.user import User
from app.security import get_current_user
from app.services.cascade_detector import detect_cascades

router = APIRouter(prefix="/v1/portfolio", tags=["portfolio"])


# ---------------------------------------------------------------------------
# Pydantic schemas — PortfolioContract
# ---------------------------------------------------------------------------

class PortfolioContractCreate(BaseModel):
    name: str
    counterparty_name: str
    our_role: str = Field(..., description="buyer | seller | subcontractor | prime")
    contract_type: str = Field(
        ..., description="it_services | goods | construction | consulting | other"
    )
    contract_value_cad: Optional[float] = None
    currency: str = "CAD"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = "active"
    jurisdiction_code: Optional[str] = None
    notes: Optional[str] = None


class PortfolioContractUpdate(BaseModel):
    name: Optional[str] = None
    counterparty_name: Optional[str] = None
    our_role: Optional[str] = None
    contract_type: Optional[str] = None
    contract_value_cad: Optional[float] = None
    currency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    jurisdiction_code: Optional[str] = None
    notes: Optional[str] = None


class PortfolioContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    counterparty_name: str
    our_role: str
    contract_type: str
    contract_value_cad: Optional[float] = None
    currency: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str
    jurisdiction_code: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Pydantic schemas — Obligation
# ---------------------------------------------------------------------------

class ObligationCreate(BaseModel):
    obligation_type: str = Field(
        ...,
        description=(
            "payment | delivery | sla | data_handling | reporting | "
            "renewal | termination_notice | indemnity | other"
        ),
    )
    party: str = Field(..., description="us | counterparty")
    description: str
    deadline_days_from_trigger: Optional[int] = None
    trigger_event: Optional[str] = None
    absolute_deadline: Optional[date] = None
    penalty_formula: Optional[str] = None
    penalty_amount_cad: Optional[float] = None
    liability_cap_cad: Optional[float] = None
    source_clause_text: Optional[str] = None
    source_clause_key: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ObligationUpdate(BaseModel):
    obligation_type: Optional[str] = None
    party: Optional[str] = None
    description: Optional[str] = None
    deadline_days_from_trigger: Optional[int] = None
    trigger_event: Optional[str] = None
    absolute_deadline: Optional[date] = None
    penalty_formula: Optional[str] = None
    penalty_amount_cad: Optional[float] = None
    liability_cap_cad: Optional[float] = None
    source_clause_text: Optional[str] = None
    source_clause_key: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ObligationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    user_id: str
    obligation_type: str
    party: str
    description: str
    deadline_days_from_trigger: Optional[int] = None
    trigger_event: Optional[str] = None
    absolute_deadline: Optional[date] = None
    penalty_formula: Optional[str] = None
    penalty_amount_cad: Optional[float] = None
    liability_cap_cad: Optional[float] = None
    source_clause_text: Optional[str] = None
    source_clause_key: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


def _serialize_obligation(o: Obligation) -> ObligationRead:
    """Convert an Obligation ORM row to its read schema, hiding empty metadata."""
    payload = ObligationRead.model_validate(o)
    if not payload.metadata_json:
        payload = payload.model_copy(update={"metadata_json": None})
    return payload


# ---------------------------------------------------------------------------
# Ownership helpers
# ---------------------------------------------------------------------------

def _get_owned_contract(
    contract_id: str, db: Session, current_user: User
) -> PortfolioContract:
    """Fetch a contract owned by current_user. Raises 404 otherwise."""
    contract = (
        db.query(PortfolioContract)
        .filter(
            PortfolioContract.id == contract_id,
            PortfolioContract.user_id == str(current_user.id),
        )
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


def _get_owned_obligation(
    obligation_id: str, db: Session, current_user: User
) -> Obligation:
    """Fetch an obligation owned by current_user. Raises 404 otherwise."""
    obligation = (
        db.query(Obligation)
        .filter(
            Obligation.id == obligation_id,
            Obligation.user_id == str(current_user.id),
        )
        .first()
    )
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")
    return obligation


# ---------------------------------------------------------------------------
# Contract endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/contracts",
    response_model=PortfolioContractRead,
    status_code=status.HTTP_201_CREATED,
)
def create_contract(
    payload: PortfolioContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioContractRead:
    contract = PortfolioContract(
        user_id=str(current_user.id),
        **payload.model_dump(),
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return PortfolioContractRead.model_validate(contract)


@router.get("/contracts", response_model=List[PortfolioContractRead])
def list_contracts(
    status_filter: Optional[str] = Query(None, alias="status"),
    contract_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PortfolioContractRead]:
    q = db.query(PortfolioContract).filter(
        PortfolioContract.user_id == str(current_user.id)
    )
    if status_filter is not None:
        q = q.filter(PortfolioContract.status == status_filter)
    if contract_type is not None:
        q = q.filter(PortfolioContract.contract_type == contract_type)
    rows = q.order_by(PortfolioContract.created_at.desc()).all()
    return [PortfolioContractRead.model_validate(r) for r in rows]


@router.get("/contracts/{contract_id}", response_model=PortfolioContractRead)
def get_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioContractRead:
    contract = _get_owned_contract(contract_id, db, current_user)
    return PortfolioContractRead.model_validate(contract)


@router.patch("/contracts/{contract_id}", response_model=PortfolioContractRead)
def update_contract(
    contract_id: str,
    payload: PortfolioContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioContractRead:
    contract = _get_owned_contract(contract_id, db, current_user)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(contract, key, value)
    db.commit()
    db.refresh(contract)
    return PortfolioContractRead.model_validate(contract)


@router.delete("/contracts/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    contract = _get_owned_contract(contract_id, db, current_user)
    db.delete(contract)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Obligation endpoints — nested under a contract
# ---------------------------------------------------------------------------

@router.post(
    "/contracts/{contract_id}/obligations",
    response_model=ObligationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_obligation(
    contract_id: str,
    payload: ObligationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ObligationRead:
    contract = _get_owned_contract(contract_id, db, current_user)

    data = payload.model_dump()
    if data.get("metadata_json") is None:
        data["metadata_json"] = {}

    obligation = Obligation(
        contract_id=contract.id,
        user_id=str(current_user.id),
        **data,
    )
    db.add(obligation)
    db.commit()
    db.refresh(obligation)
    return _serialize_obligation(obligation)


@router.get(
    "/contracts/{contract_id}/obligations",
    response_model=List[ObligationRead],
)
def list_contract_obligations(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ObligationRead]:
    # Ownership check first — 404 if user doesn't own the contract
    _get_owned_contract(contract_id, db, current_user)
    rows = (
        db.query(Obligation)
        .filter(Obligation.contract_id == contract_id)
        .order_by(Obligation.created_at.asc())
        .all()
    )
    return [_serialize_obligation(o) for o in rows]


# ---------------------------------------------------------------------------
# Obligation endpoints — portfolio-wide (hot path for cascade detector)
# ---------------------------------------------------------------------------

@router.get("/obligations", response_model=List[ObligationRead])
def list_all_obligations(
    obligation_type: Optional[str] = Query(None),
    party: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ObligationRead]:
    """
    List every obligation across the current user's entire portfolio.

    Filters by user_id first to leverage the indexed column — this is the
    hot path the future cross-contract cascade detector will hit on every
    "what blows up if X slips?" query.
    """
    q = db.query(Obligation).filter(Obligation.user_id == str(current_user.id))
    if obligation_type is not None:
        q = q.filter(Obligation.obligation_type == obligation_type)
    if party is not None:
        q = q.filter(Obligation.party == party)
    rows = q.order_by(Obligation.created_at.asc()).all()
    return [_serialize_obligation(o) for o in rows]


@router.patch("/obligations/{obligation_id}", response_model=ObligationRead)
def update_obligation(
    obligation_id: str,
    payload: ObligationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ObligationRead:
    obligation = _get_owned_obligation(obligation_id, db, current_user)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(obligation, key, value)
    db.commit()
    db.refresh(obligation)
    return _serialize_obligation(obligation)


@router.delete(
    "/obligations/{obligation_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_obligation(
    obligation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    obligation = _get_owned_obligation(obligation_id, db, current_user)
    db.delete(obligation)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Cascade detection — Step 2 of the Blast Radius engine
# ---------------------------------------------------------------------------

@router.get("/cascade-check")
def cascade_check_portfolio(
    include_draft: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Run the deterministic cross-contract cascade detector across the
    current user's entire active portfolio. Set include_draft=true to
    also fold in draft contracts (useful for "what if I sign this?").
    """
    return detect_cascades(
        db=db,
        user_id=str(current_user.id),
        focus_contract_id=None,
        include_draft=include_draft,
    )


@router.get("/contracts/{contract_id}/cascade-check")
def cascade_check_for_contract(
    contract_id: str,
    include_draft: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Cascade detector focused on a single contract — only conflicts that
    involve this contract are returned. Returns 404 if the contract is
    not owned by the current user.
    """
    # Ownership check first — 404 leaks no data about other users.
    _get_owned_contract(contract_id, db, current_user)
    return detect_cascades(
        db=db,
        user_id=str(current_user.id),
        focus_contract_id=contract_id,
        include_draft=include_draft,
    )
