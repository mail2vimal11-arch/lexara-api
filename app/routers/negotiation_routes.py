"""
Negotiation Simulator endpoints — /v1/negotiation/

Routes:
    POST   /v1/negotiation/start                   Create a new negotiation session
    GET    /v1/negotiation/{session_id}             Retrieve full session state
    POST   /v1/negotiation/{session_id}/propose     User proposes a clause revision
    POST   /v1/negotiation/{session_id}/respond     User responds to opponent counter
    POST   /v1/negotiation/{session_id}/trade       User proposes a cross-clause trade
    GET    /v1/negotiation/{session_id}/batna       Get BATNA assessment
    POST   /v1/negotiation/{session_id}/scenario    Run a post-signature cascade simulation
    GET    /v1/negotiation/{session_id}/ledger      Get the full concession ledger
    POST   /v1/negotiation/{session_id}/invite      Generate multi-party invite token
    POST   /v1/negotiation/join/{token}             Join as opposing counsel
    POST   /v1/negotiation/{session_id}/export      Export agreed contract text
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.negotiation import (
    NegotiationClause,
    NegotiationConcession,
    NegotiationRound,
    NegotiationSession,
)
from app.security import get_current_user
from app.services.audit_service import log_action
from app.services.clause_weights import classify_move, clause_weight

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Negotiation"])


# ---------------------------------------------------------------------------
# BATNA initialisation helper
# ---------------------------------------------------------------------------

def _initial_batna_scores(vendor_count_estimate: Optional[int]) -> tuple[float, float]:
    """
    Return (user_batna, opponent_batna) based on market concentration.

    vendor_count_estimate encoding:
        1    = sole source
        2–3  = limited competition
        4–10 = moderate competition
        11+  = ample competition (11 is used as the sentinel for 10+)
    """
    if vendor_count_estimate is None:
        return 50.0, 50.0
    if vendor_count_estimate == 1:
        return 20.0, 90.0
    if vendor_count_estimate <= 3:
        return 45.0, 70.0
    if vendor_count_estimate <= 10:
        return 65.0, 50.0
    # 11+ vendors
    return 85.0, 30.0


# ---------------------------------------------------------------------------
# Ownership validation helper
# ---------------------------------------------------------------------------

def _validate_session(
    session_id: str,
    db: Session,
    current_user,
    require_ownership: bool = True,
) -> NegotiationSession:
    """
    Fetch a NegotiationSession by its public session_id string.

    Raises 404 if not found, 403 if the caller does not own the session
    and require_ownership is True.
    """
    session = (
        db.query(NegotiationSession)
        .filter(NegotiationSession.session_id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Negotiation session not found")
    if require_ownership and session.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied: you do not own this session")
    return session


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class NegotiationIntakeRequest(BaseModel):
    party_type: str
    jurisdiction_code: str
    commodity_category_code: Optional[str] = None
    contract_value_cad: Optional[float] = None
    vendor_count_estimate: Optional[int] = None
    fiscal_quarter_end_pressure: bool = False
    non_negotiables: List[str] = []
    tradeable_items: List[str] = []
    original_contract_text: Optional[str] = None
    # Clauses pre-identified from the contract analysis page
    clauses: List[dict] = []


class ProposeRequest(BaseModel):
    clause_key: str
    proposed_text: str


class RespondRequest(BaseModel):
    clause_key: str
    action: str  # "accept" | "reject" | "counter"
    counter_text: Optional[str] = None


class TradeRequest(BaseModel):
    offered_clause_key: str
    offered_text: str
    requested_clause_key: str
    rationale: str


class ScenarioRequest(BaseModel):
    clause_key: str
    scenario_type: str  # "enforcement" | "breach" | "dispute" | "worst_case"


class SessionResponse(BaseModel):
    session_id: str
    status: str
    party_type: str
    jurisdiction_code: str
    rounds_completed: int
    batna_score: Optional[float]
    batna_score_opponent: Optional[float]
    total_risk_reduction_cad: Optional[float]
    total_concessions_cad: Optional[float]
    clauses: List[dict]
    recent_rounds: List[dict]


# ---------------------------------------------------------------------------
# Internal serialisation helpers
# ---------------------------------------------------------------------------

def _serialise_clause(clause: NegotiationClause) -> dict:
    return {
        "id": clause.id,
        "clause_key": clause.clause_key,
        "clause_title": clause.clause_title,
        "original_text": clause.original_text,
        "your_proposed_text": clause.your_proposed_text,
        "opponent_proposed_text": clause.opponent_proposed_text,
        "agreed_text": clause.agreed_text,
        "state": clause.state,
        "is_user_non_negotiable": clause.is_user_non_negotiable,
        "is_user_tradeable": clause.is_user_tradeable,
        "risk_severity": clause.risk_severity,
        "risk_exposure_cad": float(clause.risk_exposure_cad) if clause.risk_exposure_cad is not None else None,
        "risk_reduction_achieved_cad": float(clause.risk_reduction_achieved_cad) if clause.risk_reduction_achieved_cad is not None else None,
        "clause_type": clause.clause_type,
        "opponent_rejection_count": clause.opponent_rejection_count,
        "user_rejection_count": clause.user_rejection_count,
        "jurisprudence_article_ids": clause.jurisprudence_article_ids,
        "display_order": clause.display_order,
    }


def _serialise_round(rnd: NegotiationRound) -> dict:
    clause = getattr(rnd, "clause", None)
    clause_type = getattr(clause, "clause_type", None) if clause else None
    risk_severity = getattr(clause, "risk_severity", None) if clause else None

    return {
        "id": rnd.id,
        "clause_id": rnd.clause_id,
        "round_number": rnd.round_number,
        "actor": rnd.actor,
        "action": rnd.action,
        "proposed_text": rnd.proposed_text,
        "response_text": rnd.response_text,
        "trade_offer": rnd.trade_offer,
        "dollar_value_cad": float(rnd.dollar_value_cad) if rnd.dollar_value_cad is not None else None,
        "ai_confidence": rnd.ai_confidence,
        "move_quality": classify_move(rnd.action, rnd.ai_confidence, clause_type, risk_severity),
        "clause_weight": clause_weight(clause_type),
        "created_at": rnd.created_at.isoformat() if rnd.created_at else None,
    }


def _build_session_response(session: NegotiationSession) -> SessionResponse:
    clauses_data = [_serialise_clause(c) for c in session.clauses]

    # Return the 10 most recent rounds across all clauses
    all_rounds = sorted(session.rounds, key=lambda r: r.id, reverse=True)[:10]
    recent_rounds_data = [_serialise_round(r) for r in reversed(all_rounds)]

    return SessionResponse(
        session_id=session.session_id,
        status=session.status,
        party_type=session.party_type,
        jurisdiction_code=session.jurisdiction_code,
        rounds_completed=session.rounds_completed,
        batna_score=session.batna_score,
        batna_score_opponent=session.batna_score_opponent,
        total_risk_reduction_cad=float(session.total_risk_reduction_cad) if session.total_risk_reduction_cad is not None else None,
        total_concessions_cad=float(session.total_concessions_cad) if session.total_concessions_cad is not None else None,
        clauses=clauses_data,
        recent_rounds=recent_rounds_data,
    )


# ---------------------------------------------------------------------------
# POST /v1/negotiation/start
# ---------------------------------------------------------------------------

@router.post("/start", response_model=SessionResponse, status_code=201)
def start_negotiation(
    request: NegotiationIntakeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new NegotiationSession from the intake form.

    Sets initial BATNA scores based on vendor_count_estimate:
        1     → user 20 / opponent 90  (sole source: minimal user leverage)
        2–3   → user 45 / opponent 70
        4–10  → user 65 / opponent 50
        10+   → user 85 / opponent 30  (competitive market: strong user leverage)

    Also creates one NegotiationClause row for each clause supplied in the
    request, honouring the non_negotiables and tradeable_items lists.
    """
    try:
        session_id = f"neg_{uuid.uuid4().hex[:12]}"
        user_batna, opponent_batna = _initial_batna_scores(request.vendor_count_estimate)

        session = NegotiationSession(
            session_id=session_id,
            user_id=str(current_user.id),
            party_type=request.party_type,
            jurisdiction_code=request.jurisdiction_code,
            commodity_category_code=request.commodity_category_code,
            contract_value_cad=request.contract_value_cad,
            vendor_count_estimate=request.vendor_count_estimate,
            fiscal_quarter_end_pressure=request.fiscal_quarter_end_pressure,
            original_contract_text=request.original_contract_text,
            non_negotiables=request.non_negotiables or [],
            tradeable_items=request.tradeable_items or [],
            batna_score=user_batna,
            batna_score_opponent=opponent_batna,
            total_risk_reduction_cad=0,
            total_concessions_cad=0,
            rounds_completed=0,
            status="active",
        )
        db.add(session)
        db.flush()  # obtain session.id before inserting clauses

        for idx, clause_data in enumerate(request.clauses):
            clause_key = clause_data.get("clause_key", f"clause_{idx + 1}")
            is_non_neg = clause_key in (request.non_negotiables or [])
            is_tradeable = clause_key in (request.tradeable_items or [])

            clause = NegotiationClause(
                session_id=session.id,
                clause_key=clause_key,
                clause_title=clause_data.get("clause_title", clause_key),
                original_text=clause_data.get("original_text", ""),
                state="your_move",
                is_user_non_negotiable=is_non_neg,
                is_user_tradeable=is_tradeable,
                risk_severity=clause_data.get("risk_severity"),
                risk_exposure_cad=clause_data.get("risk_exposure_cad"),
                clause_type=clause_data.get("clause_type"),
                display_order=idx,
            )
            db.add(clause)

        db.commit()
        db.refresh(session)

        log_action(
            db,
            "NEGOTIATION_STARTED",
            {
                "session_id": session_id,
                "party_type": request.party_type,
                "jurisdiction_code": request.jurisdiction_code,
                "clause_count": len(request.clauses),
                "user_batna": user_batna,
                "opponent_batna": opponent_batna,
            },
            user_id=str(current_user.id),
        )

        return _build_session_response(session)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to start negotiation session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create negotiation session")


# ---------------------------------------------------------------------------
# GET /v1/negotiation/{session_id}
# ---------------------------------------------------------------------------

@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return the full current state of a negotiation session.
    Only the session owner may retrieve it.
    """
    try:
        session = _validate_session(session_id, db, current_user)
        return _build_session_response(session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve negotiation session")


# ---------------------------------------------------------------------------
# POST /v1/negotiation/{session_id}/propose
# ---------------------------------------------------------------------------

@router.post("/{session_id}/propose")
def propose_clause(
    session_id: str,
    request: ProposeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    User proposes a text revision for a clause.

    Flow:
      1. Persist the user's proposal as a NegotiationRound (actor="user", action="propose").
      2. Set clause state to "opponent_move".
      3. Call negotiation_ai.get_opponent_response() for the AI counter.
      4. Persist the AI response as another NegotiationRound (actor="opponent").
      5. Update clause state based on the opponent's action.
      6. If the opponent accepts, record a NegotiationConcession("gained") and
         update the clause's risk_reduction_achieved_cad and the session total.

    Returns the opponent's action, response text, proposed text, and new clause state.
    """
    try:
        session = _validate_session(session_id, db, current_user)

        clause = (
            db.query(NegotiationClause)
            .filter(
                NegotiationClause.session_id == session.id,
                NegotiationClause.clause_key == request.clause_key,
            )
            .first()
        )
        if not clause:
            raise HTTPException(
                status_code=404,
                detail=f"Clause '{request.clause_key}' not found in this session",
            )

        if clause.state == "agreed":
            raise HTTPException(
                status_code=400,
                detail="This clause has already been agreed — no further proposals accepted",
            )

        # Count existing rounds for this clause to derive round_number
        existing_round_count = (
            db.query(NegotiationRound)
            .filter(NegotiationRound.clause_id == clause.id)
            .count()
        )
        next_round_number = existing_round_count + 1

        # Persist user proposal
        clause.your_proposed_text = request.proposed_text
        clause.state = "opponent_move"

        user_round = NegotiationRound(
            session_id=session.id,
            clause_id=clause.id,
            round_number=next_round_number,
            actor="user",
            action="propose",
            proposed_text=request.proposed_text,
            response_text=f"User proposed revision for clause '{request.clause_key}'.",
        )
        db.add(user_round)
        db.flush()

        # Ask the AI opponent for a response
        opponent_action = "counter"
        opponent_response_text = "The opposing party is reviewing your proposal."
        opponent_proposed_text = None
        ai_confidence = None

        try:
            from app.services import negotiation_ai  # lazy import to avoid circular dependency

            ai_result = negotiation_ai.get_opponent_response(
                session=session,
                clause=clause,
                user_proposed_text=request.proposed_text,
                db=db,
            )
            opponent_action = ai_result.get("action", "counter")
            opponent_response_text = ai_result.get("response_text", opponent_response_text)
            opponent_proposed_text = ai_result.get("proposed_text")
            ai_confidence = ai_result.get("ai_confidence")
        except ImportError:
            logger.warning("negotiation_ai service not yet available — using placeholder response")
        except Exception as ai_err:
            logger.error(f"AI opponent response failed for session {session_id}: {ai_err}", exc_info=True)
            opponent_response_text = (
                "The AI negotiation service is temporarily unavailable. "
                "Your proposal has been recorded. Please try again shortly."
            )

        # Persist opponent round
        opponent_round = NegotiationRound(
            session_id=session.id,
            clause_id=clause.id,
            round_number=next_round_number + 1,
            actor="opponent",
            action=opponent_action,
            proposed_text=opponent_proposed_text,
            response_text=opponent_response_text,
            ai_confidence=ai_confidence,
        )
        db.add(opponent_round)

        # Update clause state based on opponent's decision
        if opponent_action == "accept":
            clause.state = "agreed"
            clause.agreed_text = request.proposed_text
            # Record as a gained concession
            gained_value = float(clause.risk_exposure_cad) if clause.risk_exposure_cad else None
            clause.risk_reduction_achieved_cad = gained_value

            db.flush()

            concession = NegotiationConcession(
                session_id=session.id,
                clause_id=clause.id,
                round_id=opponent_round.id,
                direction="gained",
                description=(
                    f"Opponent accepted proposed revision for '{clause.clause_title}'. "
                    f"Risk exposure eliminated."
                ),
                estimated_value_cad=gained_value,
            )
            db.add(concession)

            # Update session totals
            if gained_value:
                current_reduction = float(session.total_risk_reduction_cad or 0)
                session.total_risk_reduction_cad = current_reduction + gained_value

        elif opponent_action == "reject":
            clause.state = "your_move"
            clause.opponent_rejection_count = (clause.opponent_rejection_count or 0) + 1
        elif opponent_action == "counter":
            clause.state = "your_move"
            clause.opponent_proposed_text = opponent_proposed_text
        elif opponent_action == "withdraw":
            clause.state = "withdrawn"
        else:
            # Fallback: treat unknown actions as a counter
            clause.state = "your_move"
            clause.opponent_proposed_text = opponent_proposed_text

        session.rounds_completed = (session.rounds_completed or 0) + 1
        session.updated_at = datetime.utcnow()

        db.commit()

        log_action(
            db,
            "NEGOTIATION_PROPOSE",
            {
                "session_id": session_id,
                "clause_key": request.clause_key,
                "opponent_action": opponent_action,
                "round_number": next_round_number,
            },
            user_id=str(current_user.id),
        )

        return {
            "clause_key": request.clause_key,
            "opponent_action": opponent_action,
            "opponent_response_text": opponent_response_text,
            "opponent_proposed_text": opponent_proposed_text,
            "new_state": clause.state,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Propose failed for session {session_id}, clause {request.clause_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process clause proposal")


# ---------------------------------------------------------------------------
# POST /v1/negotiation/{session_id}/respond
# ---------------------------------------------------------------------------

@router.post("/{session_id}/respond")
def respond_to_clause(
    session_id: str,
    request: RespondRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    User responds to an opponent counter-proposal.

    action = "accept":
        Mark clause as agreed, create concession entries for both sides,
        and update the session risk-reduction total.

    action = "reject":
        Increment user_rejection_count and set state back to "your_move"
        so the user can propose a new revision.

    action = "counter":
        Update your_proposed_text with counter_text, get a new AI opponent
        response, and update clause state accordingly.

    Returns {clause_key, new_state, updated_ledger}.
    """
    try:
        session = _validate_session(session_id, db, current_user)

        clause = (
            db.query(NegotiationClause)
            .filter(
                NegotiationClause.session_id == session.id,
                NegotiationClause.clause_key == request.clause_key,
            )
            .first()
        )
        if not clause:
            raise HTTPException(
                status_code=404,
                detail=f"Clause '{request.clause_key}' not found in this session",
            )

        if clause.state == "agreed":
            raise HTTPException(
                status_code=400,
                detail="This clause has already been agreed",
            )

        valid_actions = {"accept", "reject", "counter"}
        if request.action not in valid_actions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action '{request.action}'. Must be one of: {', '.join(sorted(valid_actions))}",
            )

        if request.action == "counter" and not request.counter_text:
            raise HTTPException(
                status_code=400,
                detail="counter_text is required when action is 'counter'",
            )

        existing_round_count = (
            db.query(NegotiationRound)
            .filter(NegotiationRound.clause_id == clause.id)
            .count()
        )
        next_round_number = existing_round_count + 1

        updated_ledger: list[dict] = []

        # ── Accept ──────────────────────────────────────────────────────────

        if request.action == "accept":
            accepted_text = clause.opponent_proposed_text or clause.original_text
            clause.agreed_text = accepted_text
            clause.state = "agreed"

            user_round = NegotiationRound(
                session_id=session.id,
                clause_id=clause.id,
                round_number=next_round_number,
                actor="user",
                action="accept",
                proposed_text=accepted_text,
                response_text=f"User accepted the opponent's proposal for '{clause.clause_title}'.",
            )
            db.add(user_round)
            db.flush()

            # Both sides concede — user gave ground; record for ledger
            gave_concession = NegotiationConcession(
                session_id=session.id,
                clause_id=clause.id,
                round_id=user_round.id,
                direction="gave",
                description=(
                    f"User accepted opponent's text for '{clause.clause_title}', "
                    f"conceding the user's preferred wording."
                ),
                estimated_value_cad=None,
            )
            db.add(gave_concession)

            # If the opponent had offered something better than the original,
            # record any residual risk reduction as "gained"
            if clause.risk_exposure_cad and clause.risk_reduction_achieved_cad is None:
                # Partial credit: we accepted their counter but it still reduces some risk
                partial_reduction = float(clause.risk_exposure_cad) * 0.5
                clause.risk_reduction_achieved_cad = partial_reduction

                gained_concession = NegotiationConcession(
                    session_id=session.id,
                    clause_id=clause.id,
                    round_id=user_round.id,
                    direction="gained",
                    description=(
                        f"Partial risk reduction achieved for '{clause.clause_title}' "
                        f"by accepting opponent's counter-proposal."
                    ),
                    estimated_value_cad=partial_reduction,
                )
                db.add(gained_concession)

                current_reduction = float(session.total_risk_reduction_cad or 0)
                session.total_risk_reduction_cad = current_reduction + partial_reduction

            conceded_amount = float(clause.risk_exposure_cad or 0) * 0.5
            current_concessions = float(session.total_concessions_cad or 0)
            session.total_concessions_cad = current_concessions + conceded_amount

            db.flush()

            updated_ledger = [
                {
                    "direction": "gave",
                    "clause_key": request.clause_key,
                    "description": f"Accepted opponent's revision for '{clause.clause_title}'",
                    "estimated_value_cad": None,
                }
            ]

        # ── Reject ──────────────────────────────────────────────────────────

        elif request.action == "reject":
            clause.state = "your_move"
            clause.user_rejection_count = (clause.user_rejection_count or 0) + 1

            user_round = NegotiationRound(
                session_id=session.id,
                clause_id=clause.id,
                round_number=next_round_number,
                actor="user",
                action="reject",
                proposed_text=None,
                response_text=f"User rejected the opponent's proposal for '{clause.clause_title}'.",
            )
            db.add(user_round)

        # ── Counter ─────────────────────────────────────────────────────────

        elif request.action == "counter":
            clause.your_proposed_text = request.counter_text
            clause.state = "opponent_move"

            user_round = NegotiationRound(
                session_id=session.id,
                clause_id=clause.id,
                round_number=next_round_number,
                actor="user",
                action="counter",
                proposed_text=request.counter_text,
                response_text=f"User submitted a counter-proposal for '{clause.clause_title}'.",
            )
            db.add(user_round)
            db.flush()

            # Get AI opponent response to the counter
            opponent_action = "counter"
            opponent_response_text = "The opposing party is reviewing your counter-proposal."
            opponent_proposed_text = None
            ai_confidence = None

            try:
                from app.services import negotiation_ai  # lazy import

                ai_result = negotiation_ai.get_opponent_response(
                    session=session,
                    clause=clause,
                    user_proposed_text=request.counter_text,
                    db=db,
                )
                opponent_action = ai_result.get("action", "counter")
                opponent_response_text = ai_result.get("response_text", opponent_response_text)
                opponent_proposed_text = ai_result.get("proposed_text")
                ai_confidence = ai_result.get("ai_confidence")
            except ImportError:
                logger.warning("negotiation_ai service not yet available")
            except Exception as ai_err:
                logger.error(
                    f"AI counter-response failed for session {session_id}: {ai_err}",
                    exc_info=True,
                )
                opponent_response_text = (
                    "The AI negotiation service is temporarily unavailable. "
                    "Your counter-proposal has been recorded."
                )

            opponent_round = NegotiationRound(
                session_id=session.id,
                clause_id=clause.id,
                round_number=next_round_number + 1,
                actor="opponent",
                action=opponent_action,
                proposed_text=opponent_proposed_text,
                response_text=opponent_response_text,
                ai_confidence=ai_confidence,
            )
            db.add(opponent_round)

            if opponent_action == "accept":
                clause.state = "agreed"
                clause.agreed_text = request.counter_text
                gained_value = float(clause.risk_exposure_cad) if clause.risk_exposure_cad else None
                clause.risk_reduction_achieved_cad = gained_value

                db.flush()

                concession = NegotiationConcession(
                    session_id=session.id,
                    clause_id=clause.id,
                    round_id=opponent_round.id,
                    direction="gained",
                    description=(
                        f"Opponent accepted counter-proposal for '{clause.clause_title}'."
                    ),
                    estimated_value_cad=gained_value,
                )
                db.add(concession)

                if gained_value:
                    current_reduction = float(session.total_risk_reduction_cad or 0)
                    session.total_risk_reduction_cad = current_reduction + gained_value
            elif opponent_action == "reject":
                clause.state = "your_move"
                clause.opponent_rejection_count = (clause.opponent_rejection_count or 0) + 1
            elif opponent_action == "counter":
                clause.state = "your_move"
                clause.opponent_proposed_text = opponent_proposed_text
            else:
                clause.state = "your_move"

        session.rounds_completed = (session.rounds_completed or 0) + 1
        session.updated_at = datetime.utcnow()

        db.commit()

        log_action(
            db,
            "NEGOTIATION_RESPOND",
            {
                "session_id": session_id,
                "clause_key": request.clause_key,
                "action": request.action,
            },
            user_id=str(current_user.id),
        )

        return {
            "clause_key": request.clause_key,
            "new_state": clause.state,
            "updated_ledger": updated_ledger,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Respond failed for session {session_id}, clause {request.clause_key}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to process clause response")


# ---------------------------------------------------------------------------
# POST /v1/negotiation/{session_id}/trade
# ---------------------------------------------------------------------------

@router.post("/{session_id}/trade")
def propose_trade(
    session_id: str,
    request: TradeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    User proposes a cross-clause trade (give concession on one clause in
    exchange for a concession on another).

    Persists a NegotiationRound with action="trade_offer" on the offered clause,
    then calls negotiation_ai.evaluate_trade() for the opponent's decision.

    Returns {trade_accepted, rationale, updated_clauses}.
    """
    try:
        session = _validate_session(session_id, db, current_user)

        offered_clause = (
            db.query(NegotiationClause)
            .filter(
                NegotiationClause.session_id == session.id,
                NegotiationClause.clause_key == request.offered_clause_key,
            )
            .first()
        )
        if not offered_clause:
            raise HTTPException(
                status_code=404,
                detail=f"Offered clause '{request.offered_clause_key}' not found",
            )

        requested_clause = (
            db.query(NegotiationClause)
            .filter(
                NegotiationClause.session_id == session.id,
                NegotiationClause.clause_key == request.requested_clause_key,
            )
            .first()
        )
        if not requested_clause:
            raise HTTPException(
                status_code=404,
                detail=f"Requested clause '{request.requested_clause_key}' not found",
            )

        trade_payload = {
            "offered_clause_key": request.offered_clause_key,
            "offered_text": request.offered_text,
            "requested_clause_key": request.requested_clause_key,
            "requested_text": None,
            "rationale": request.rationale,
        }

        existing_round_count = (
            db.query(NegotiationRound)
            .filter(NegotiationRound.clause_id == offered_clause.id)
            .count()
        )

        offered_clause.state = "trade_pending"
        requested_clause.state = "trade_pending"

        trade_round = NegotiationRound(
            session_id=session.id,
            clause_id=offered_clause.id,
            round_number=existing_round_count + 1,
            actor="user",
            action="trade_offer",
            proposed_text=request.offered_text,
            response_text=(
                f"User proposes trade: accept '{request.offered_clause_key}' revision "
                f"in exchange for concession on '{request.requested_clause_key}'. "
                f"Rationale: {request.rationale}"
            ),
            trade_offer=trade_payload,
        )
        db.add(trade_round)
        db.flush()

        # Ask AI to evaluate the trade
        trade_accepted = False
        ai_rationale = "The opposing party is considering the trade offer."
        updated_clauses: list[str] = []

        try:
            from app.services import negotiation_ai  # lazy import

            trade_result = negotiation_ai.evaluate_trade(
                session=session,
                offered_clause=offered_clause,
                requested_clause=requested_clause,
                offered_text=request.offered_text,
                rationale=request.rationale,
                db=db,
            )
            trade_accepted = trade_result.get("accepted", False)
            ai_rationale = trade_result.get("rationale", ai_rationale)
            updated_clauses = trade_result.get("updated_clauses", [])
        except ImportError:
            logger.warning("negotiation_ai service not yet available — trade evaluation skipped")
            ai_rationale = (
                "The AI negotiation service is temporarily unavailable. "
                "Your trade offer has been recorded."
            )
        except Exception as ai_err:
            logger.error(
                f"Trade evaluation failed for session {session_id}: {ai_err}",
                exc_info=True,
            )
            ai_rationale = (
                "The AI negotiation service encountered an error evaluating your trade. "
                "Please try again."
            )

        opponent_action = "trade_accept" if trade_accepted else "trade_reject"

        response_round = NegotiationRound(
            session_id=session.id,
            clause_id=offered_clause.id,
            round_number=existing_round_count + 2,
            actor="opponent",
            action=opponent_action,
            response_text=ai_rationale,
            trade_offer=trade_payload,
        )
        db.add(response_round)

        if trade_accepted:
            offered_clause.state = "agreed"
            offered_clause.agreed_text = request.offered_text
            requested_clause.state = "agreed"
            updated_clauses = [request.offered_clause_key, request.requested_clause_key]

            db.flush()

            # Record the trade as both gave and gained
            gave_concession = NegotiationConcession(
                session_id=session.id,
                clause_id=offered_clause.id,
                round_id=response_round.id,
                direction="gave",
                description=(
                    f"Conceded '{offered_clause.clause_title}' as part of trade "
                    f"for '{requested_clause.clause_title}'."
                ),
                estimated_value_cad=float(offered_clause.risk_exposure_cad) if offered_clause.risk_exposure_cad else None,
            )
            db.add(gave_concession)

            gained_concession = NegotiationConcession(
                session_id=session.id,
                clause_id=requested_clause.id,
                round_id=response_round.id,
                direction="gained",
                description=(
                    f"Won concession on '{requested_clause.clause_title}' "
                    f"in exchange for '{offered_clause.clause_title}'."
                ),
                estimated_value_cad=float(requested_clause.risk_exposure_cad) if requested_clause.risk_exposure_cad else None,
            )
            db.add(gained_concession)

        else:
            offered_clause.state = "your_move"
            requested_clause.state = "your_move"

        session.rounds_completed = (session.rounds_completed or 0) + 1
        session.updated_at = datetime.utcnow()

        db.commit()

        log_action(
            db,
            "NEGOTIATION_TRADE",
            {
                "session_id": session_id,
                "offered_clause_key": request.offered_clause_key,
                "requested_clause_key": request.requested_clause_key,
                "trade_accepted": trade_accepted,
            },
            user_id=str(current_user.id),
        )

        return {
            "trade_accepted": trade_accepted,
            "rationale": ai_rationale,
            "updated_clauses": updated_clauses,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Trade failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process trade offer")


# ---------------------------------------------------------------------------
# GET /v1/negotiation/{session_id}/batna
# ---------------------------------------------------------------------------

@router.get("/{session_id}/batna")
def get_batna(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return the current BATNA assessment for the session.

    Includes leverage classifications, strategic advice, and a list of
    clause keys whose concession would weaken the user's negotiating position.
    """
    try:
        session = _validate_session(session_id, db, current_user)

        user_score = session.batna_score or 50.0
        opponent_score = session.batna_score_opponent or 50.0

        # Classify user leverage
        if user_score >= 75:
            user_leverage = "strong"
        elif user_score >= 55:
            user_leverage = "moderate"
        elif user_score >= 35:
            user_leverage = "weak"
        else:
            user_leverage = "critical"

        # Classify opponent leverage
        if opponent_score >= 75:
            opponent_leverage = "strong"
        elif opponent_score >= 55:
            opponent_leverage = "moderate"
        elif opponent_score >= 35:
            opponent_leverage = "weak"
        else:
            opponent_leverage = "critical"

        # Strategic advice based on relative positions
        score_gap = user_score - opponent_score
        if score_gap >= 20:
            strategic_advice = (
                "You hold strong leverage. Push for favourable terms on critical clauses "
                "before the opponent's position strengthens. This is the right moment to "
                "address liability caps and IP ownership."
            )
        elif score_gap >= 0:
            strategic_advice = (
                "Positions are roughly balanced. Focus on sequencing: resolve lower-risk "
                "clauses first to build momentum and goodwill before tackling contentious "
                "liability and termination provisions."
            )
        elif score_gap >= -20:
            strategic_advice = (
                "The opponent has a modest advantage. Consider offering a trade on a "
                "lower-priority clause to unlock movement on your must-have provisions. "
                "Avoid conceding on non-negotiables under time pressure."
            )
        else:
            strategic_advice = (
                "Your BATNA is significantly weaker. Prioritise preserving your "
                "non-negotiable clauses and explore whether there are tradeable items "
                "you can concede to improve the overall deal value. Consider whether "
                "seeking an alternative counterparty is feasible."
            )

        # Identify non-negotiable clauses still unresolved — these are the
        # clauses whose concession would most weaken the user's position
        weakening_triggers = [
            clause.clause_key
            for clause in session.clauses
            if clause.is_user_non_negotiable and clause.state not in ("agreed", "withdrawn")
        ]

        # Window assessment based on fiscal pressure and outstanding clauses
        pending_count = sum(
            1 for c in session.clauses if c.state not in ("agreed", "withdrawn")
        )
        if session.fiscal_quarter_end_pressure and pending_count > 0:
            window_assessment = (
                f"Fiscal quarter-end pressure is active. With {pending_count} clause(s) "
                f"still open, time pressure may weaken your position if you do not resolve "
                f"key items within the next 48–72 hours."
            )
        elif pending_count == 0:
            window_assessment = "All clauses have been resolved. The negotiation window is closed."
        else:
            window_assessment = (
                f"{pending_count} clause(s) remain open. No immediate time pressure detected."
            )

        return {
            "user_batna_score": user_score,
            "opponent_batna_score": opponent_score,
            "user_leverage_assessment": user_leverage,
            "opponent_leverage": opponent_leverage,
            "strategic_advice": strategic_advice,
            "weakening_triggers": weakening_triggers,
            "window_assessment": window_assessment,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BATNA assessment failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to compute BATNA assessment")


# ---------------------------------------------------------------------------
# POST /v1/negotiation/{session_id}/scenario
# ---------------------------------------------------------------------------

@router.post("/{session_id}/scenario")
def run_scenario(
    session_id: str,
    request: ScenarioRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Run a post-signature cascade simulation for a given clause.

    scenario_type values:
        enforcement  — what happens when the party attempts to enforce the clause
        breach       — what happens if the other party breaches this clause
        dispute      — how a dispute over this clause plays out through the courts
        worst_case   — maximum downside exposure under the current clause text

    Returns a timeline of events with financial exposure ranges and
    relevant jurisprudence article references.
    """
    try:
        session = _validate_session(session_id, db, current_user)

        clause = (
            db.query(NegotiationClause)
            .filter(
                NegotiationClause.session_id == session.id,
                NegotiationClause.clause_key == request.clause_key,
            )
            .first()
        )
        if not clause:
            raise HTTPException(
                status_code=404,
                detail=f"Clause '{request.clause_key}' not found in this session",
            )

        valid_scenario_types = {"enforcement", "breach", "dispute", "worst_case"}
        if request.scenario_type not in valid_scenario_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scenario_type '{request.scenario_type}'. "
                       f"Must be one of: {', '.join(sorted(valid_scenario_types))}",
            )

        scenario_timeline: list[dict] = []
        jurisprudence_refs: list[str] = clause.jurisprudence_article_ids or []

        try:
            from app.services import negotiation_ai  # lazy import

            scenario_result = negotiation_ai.run_scenario(
                session=session,
                clause=clause,
                scenario_type=request.scenario_type,
                db=db,
            )
            scenario_timeline = scenario_result.get("timeline", [])
            jurisprudence_refs = scenario_result.get("jurisprudence_refs", jurisprudence_refs)
        except ImportError:
            logger.warning("negotiation_ai service not yet available — returning placeholder scenario")
            # Build a minimal placeholder timeline so the caller gets a useful shape
            base_exposure = float(clause.risk_exposure_cad or 0)
            scenario_timeline = [
                {
                    "day": 0,
                    "event": f"Contract signed with current '{clause.clause_title}' wording.",
                    "financial_exposure_min": 0.0,
                    "financial_exposure_max": 0.0,
                },
                {
                    "day": 30,
                    "event": f"Triggering event occurs under {request.scenario_type} scenario.",
                    "financial_exposure_min": base_exposure * 0.25,
                    "financial_exposure_max": base_exposure * 0.75,
                },
                {
                    "day": 180,
                    "event": "Dispute escalated. Legal costs accumulate.",
                    "financial_exposure_min": base_exposure * 0.50,
                    "financial_exposure_max": base_exposure * 1.25,
                },
                {
                    "day": 365,
                    "event": "Matter resolved via arbitration or court judgment.",
                    "financial_exposure_min": base_exposure * 0.75,
                    "financial_exposure_max": base_exposure * 2.00,
                },
            ]
        except Exception as ai_err:
            logger.error(
                f"Scenario simulation failed for session {session_id}: {ai_err}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=503,
                detail="Scenario simulation service temporarily unavailable. Please try again.",
            )

        log_action(
            db,
            "NEGOTIATION_SCENARIO",
            {
                "session_id": session_id,
                "clause_key": request.clause_key,
                "scenario_type": request.scenario_type,
            },
            user_id=str(current_user.id),
        )

        return {
            "clause_key": request.clause_key,
            "scenario_type": request.scenario_type,
            "timeline": scenario_timeline,
            "jurisprudence_refs": jurisprudence_refs,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scenario failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to run scenario simulation")


# ---------------------------------------------------------------------------
# GET /v1/negotiation/{session_id}/ledger
# ---------------------------------------------------------------------------

@router.get("/{session_id}/ledger")
def get_ledger(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return the full concession ledger for the session, sorted by created_at.

    Separates concessions into "gave" and "gained" buckets and computes:
        net_value_cad       — gained total minus gave total
        risk_reduction_pct  — percentage of total session risk exposure recovered
    """
    try:
        session = _validate_session(session_id, db, current_user)

        all_concessions = (
            db.query(NegotiationConcession)
            .filter(NegotiationConcession.session_id == session.id)
            .order_by(NegotiationConcession.created_at.asc())
            .all()
        )

        gave: list[dict] = []
        gained: list[dict] = []
        gave_total = 0.0
        gained_total = 0.0

        for c in all_concessions:
            entry = {
                "id": c.id,
                "clause_id": c.clause_id,
                "round_id": c.round_id,
                "direction": c.direction,
                "description": c.description,
                "estimated_value_cad": float(c.estimated_value_cad) if c.estimated_value_cad is not None else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            if c.direction == "gave":
                gave.append(entry)
                gave_total += float(c.estimated_value_cad or 0)
            else:
                gained.append(entry)
                gained_total += float(c.estimated_value_cad or 0)

        net_value_cad = gained_total - gave_total

        # Compute risk reduction percentage against total session risk exposure
        total_session_exposure = sum(
            float(clause.risk_exposure_cad or 0) for clause in session.clauses
        )
        if total_session_exposure > 0:
            risk_reduction_pct = (gained_total / total_session_exposure) * 100.0
        else:
            risk_reduction_pct = 0.0

        return {
            "gave": gave,
            "gained": gained,
            "net_value_cad": round(net_value_cad, 2),
            "risk_reduction_pct": round(risk_reduction_pct, 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ledger retrieval failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve concession ledger")


# ---------------------------------------------------------------------------
# POST /v1/negotiation/{session_id}/invite
# ---------------------------------------------------------------------------

@router.post("/{session_id}/invite")
def create_invite(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate a unique multi-party invite token and a shareable URL.

    Token is a UUID4 hex string. Link expires in 48 hours.
    Only the session owner may generate an invite.

    Returns {invite_url, expires_at}.
    """
    try:
        session = _validate_session(session_id, db, current_user)

        token = uuid.uuid4().hex
        expires_at = datetime.utcnow() + timedelta(hours=48)

        session.multi_party_token = token
        session.invite_expires_at = expires_at
        session.updated_at = datetime.utcnow()

        db.commit()

        invite_url = f"/negotiation-arena.html?token={token}"

        log_action(
            db,
            "NEGOTIATION_INVITE_CREATED",
            {"session_id": session_id, "expires_at": expires_at.isoformat()},
            user_id=str(current_user.id),
        )

        return {
            "invite_url": invite_url,
            "expires_at": expires_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Invite creation failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate invite")


# ---------------------------------------------------------------------------
# POST /v1/negotiation/join/{token}
# ---------------------------------------------------------------------------

@router.post("/join/{token}")
def join_session(
    token: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Join an existing negotiation session as the opposing counsel.

    Validates that the token exists and has not expired, then sets
    multi_party_opponent_user_id to the current user's ID.

    Returns {session_id} so the caller can load the full arena state
    via GET /v1/negotiation/{session_id}.
    """
    try:
        session = (
            db.query(NegotiationSession)
            .filter(NegotiationSession.multi_party_token == token)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Invite token not found or already used")

        if session.invite_expires_at and datetime.utcnow() > session.invite_expires_at:
            raise HTTPException(
                status_code=410,
                detail="This invite link has expired. Ask the session owner to generate a new one.",
            )

        if session.user_id == str(current_user.id):
            raise HTTPException(
                status_code=400,
                detail="You cannot join your own negotiation session as the opposing party",
            )

        if session.multi_party_opponent_user_id:
            # Allow the same opponent to re-join
            if session.multi_party_opponent_user_id != str(current_user.id):
                raise HTTPException(
                    status_code=409,
                    detail="This session already has an opposing party. Contact the session owner.",
                )

        session.multi_party_opponent_user_id = str(current_user.id)
        session.updated_at = datetime.utcnow()

        db.commit()

        log_action(
            db,
            "NEGOTIATION_JOINED",
            {"session_id": session.session_id, "opponent_user_id": str(current_user.id)},
            user_id=str(current_user.id),
        )

        return {"session_id": session.session_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Join failed for token {token}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to join negotiation session")


# ---------------------------------------------------------------------------
# POST /v1/negotiation/{session_id}/export
# ---------------------------------------------------------------------------

@router.post("/{session_id}/export")
def export_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Export the final agreed contract text.

    Requires that every clause in the session is in "agreed" or "withdrawn"
    state (i.e. there are no outstanding negotiation items).

    Builds the final contract by substituting each clause's agreed_text (or
    original_text for withdrawn clauses) in display_order, then marks the
    session status as "exported".

    Returns {final_contract_text, agreed_clause_count, session_summary}.
    """
    try:
        session = _validate_session(session_id, db, current_user)

        # Check all clauses are resolved
        unresolved = [
            clause.clause_key
            for clause in session.clauses
            if clause.state not in ("agreed", "withdrawn")
        ]
        if unresolved:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot export: {len(unresolved)} clause(s) are still open: "
                    f"{', '.join(unresolved[:5])}{'…' if len(unresolved) > 5 else ''}. "
                    f"Resolve all clauses before exporting."
                ),
            )

        # Build the final contract text by assembling agreed/withdrawn clauses
        # in display_order
        sorted_clauses = sorted(session.clauses, key=lambda c: c.display_order)
        final_parts: list[str] = []
        agreed_count = 0

        for clause in sorted_clauses:
            if clause.state == "withdrawn":
                # Withdrawn clauses are omitted from the final text
                continue
            clause_text = clause.agreed_text or clause.original_text
            final_parts.append(
                f"--- {clause.clause_title} ---\n{clause_text}"
            )
            if clause.state == "agreed":
                agreed_count += 1

        final_contract_text = "\n\n".join(final_parts)

        # Mark session as exported
        session.status = "exported"
        session.updated_at = datetime.utcnow()

        db.commit()

        # Build session summary
        total_exposure = sum(float(c.risk_exposure_cad or 0) for c in session.clauses)
        total_reduction = float(session.total_risk_reduction_cad or 0)
        total_concessions = float(session.total_concessions_cad or 0)

        session_summary = {
            "session_id": session.session_id,
            "party_type": session.party_type,
            "jurisdiction_code": session.jurisdiction_code,
            "rounds_completed": session.rounds_completed,
            "agreed_clause_count": agreed_count,
            "withdrawn_clause_count": len(sorted_clauses) - agreed_count,
            "total_risk_exposure_cad": round(total_exposure, 2),
            "total_risk_reduction_cad": round(total_reduction, 2),
            "total_concessions_cad": round(total_concessions, 2),
            "net_outcome_cad": round(total_reduction - total_concessions, 2),
            "final_batna_score": session.batna_score,
        }

        log_action(
            db,
            "NEGOTIATION_EXPORTED",
            {
                "session_id": session_id,
                "agreed_clause_count": agreed_count,
                "total_risk_reduction_cad": round(total_reduction, 2),
            },
            user_id=str(current_user.id),
        )

        return {
            "final_contract_text": final_contract_text,
            "agreed_clause_count": agreed_count,
            "session_summary": session_summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Export failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export negotiation session")
