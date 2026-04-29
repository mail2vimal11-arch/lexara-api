"""
SOW Workbench API routes — /v1/workbench prefix registered in app/main.py.

Provides the full API surface for the Lexara Procurement Authoring Workbench
(Feature 2): commodity taxonomy, jurisdiction data, session lifecycle, real-time
AI guidance, section drafting, completeness analysis, and document export.

Public (no auth required):
    GET /commodities
    GET /jurisdictions

Protected (JWT Bearer required):
    POST   /session
    GET    /session/{session_id}
    POST   /guidance
    POST   /draft-section
    POST   /save
    GET    /evaluation-template
    GET    /sla-template
    POST   /analyze-completeness
    POST   /export

NOTE: /v1/workbench/commodities and /v1/workbench/jurisdictions are public.
      Add them to app/middleware/auth.py UNPROTECTED_ROUTES when the middleware
      is updated:
          "/v1/workbench/commodities",
          "/v1/workbench/jurisdictions",
"""

import uuid
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.security import get_current_user
from app.models.knowledge import (
    WorkbenchSession,
    EvaluationTemplate,
    SLATemplate,
)
from app.models.commodity import CommoditySector, CommodityCategory
from app.models.jurisdiction import Jurisdiction
from app.services import workbench_service
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class WorkbenchIntakeRequest(BaseModel):
    jurisdiction_code: str
    commodity_category_code: str
    commodity_subcategory_code: Optional[str] = None
    procurement_method: str = "RFP"  # RFP, RFQ, ITT, RFSO
    estimated_value_cad: Optional[float] = None
    known_constraints: List[str] = []  # e.g. ["SECURITY_CLEARANCE", "BILINGUAL", "INDIGENOUS_SET_ASIDE", "AODA"]
    intent_description: Optional[str] = None  # free text: "We need a vendor to migrate our HR system..."


class GuidanceRequest(BaseModel):
    session_id: str
    section_type: str  # "background", "scope", "deliverables", "mandatory_requirements", etc.
    current_text: str  # what the user has typed so far in this section
    cursor_hint: Optional[str] = None  # optional extra context from cursor position


class SectionDraftRequest(BaseModel):
    session_id: str
    section_type: str
    intent: str  # brief description of what this section should say


class SaveDraftRequest(BaseModel):
    session_id: str
    current_text: str
    completeness_score: Optional[float] = None


class ExportRequest(BaseModel):
    session_id: str
    format: str = "text"  # "text", "markdown"


class ExtractToPortfolioRequest(BaseModel):
    contract_name: str
    counterparty_name: str
    contract_type: str  # it_services | goods | construction | consulting | other


# ---------------------------------------------------------------------------
# Helper: resolve and authorise session
# ---------------------------------------------------------------------------

def _get_session_or_404(
    session_id: str,
    db: Session,
    current_user,
) -> WorkbenchSession:
    """Load a WorkbenchSession and verify the requesting user owns it."""
    session = (
        db.query(WorkbenchSession)
        .filter(WorkbenchSession.session_id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    if session.user_id and str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="You do not own this session")
    return session


# ---------------------------------------------------------------------------
# GET /commodities  (public)
# ---------------------------------------------------------------------------

@router.get("/commodities")
def get_commodities(db: Session = Depends(get_db)):
    """
    Return the full commodity taxonomy tree.
    Cached by clients for up to 1 hour (Cache-Control: max-age=3600).
    """
    sectors = (
        db.query(CommoditySector)
        .order_by(CommoditySector.display_order)
        .all()
    )

    payload = {
        "sectors": [
            {
                "code": sector.code,
                "name": sector.name,
                "icon": sector.ui_icon,
                "categories": [
                    {
                        "code": cat.code,
                        "name": cat.name,
                        "subcategories": [
                            {"code": sub.code, "name": sub.name}
                            for sub in cat.subcategories
                        ],
                    }
                    for cat in sector.categories
                ],
            }
            for sector in sectors
        ]
    }

    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ---------------------------------------------------------------------------
# GET /jurisdictions  (public)
# ---------------------------------------------------------------------------

@router.get("/jurisdictions")
def get_jurisdictions(db: Session = Depends(get_db)):
    """
    Return all Canadian procurement jurisdictions with key framework data.
    """
    jurisdictions = db.query(Jurisdiction).order_by(Jurisdiction.jtype, Jurisdiction.name).all()

    payload = {
        "jurisdictions": [
            {
                "code": j.code,
                "name": j.name,
                "jtype": j.jtype,
                "trade_agreements": j.trade_agreements or [],
                "requires_bilingual": j.requires_bilingual,
            }
            for j in jurisdictions
        ]
    }

    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ---------------------------------------------------------------------------
# POST /session  (auth required)
# ---------------------------------------------------------------------------

@router.post("/session")
async def create_session(
    request: WorkbenchIntakeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new WorkbenchSession from intake data.

    1. Resolves the best matching SOWTemplate.
    2. Calculates initial completeness score (0.0).
    3. Generates rule-based warnings from constraints / jurisdiction / value.
    4. Persists the session and returns full initialisation payload.
    """
    # Validate commodity category exists
    cat = db.query(CommodityCategory).filter(
        CommodityCategory.code == request.commodity_category_code
    ).first()
    if not cat:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown commodity_category_code: '{request.commodity_category_code}'",
        )

    # Validate jurisdiction exists
    jur = db.query(Jurisdiction).filter(
        Jurisdiction.code == request.jurisdiction_code
    ).first()
    if not jur:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown jurisdiction_code: '{request.jurisdiction_code}'",
        )

    # Find best template
    template_info = workbench_service.get_recommended_template(
        db=db,
        commodity_category_code=request.commodity_category_code,
        jurisdiction_code=request.jurisdiction_code,
        procurement_method=request.procurement_method,
    )

    sections = template_info["sections"]
    template_id = template_info["template_id"]

    # Initial completeness is always 0 — session is brand new
    completeness = workbench_service.calculate_completeness("", sections)

    # Rule-based warnings
    warnings = workbench_service.generate_warnings(
        jurisdiction_code=request.jurisdiction_code,
        commodity_category_code=request.commodity_category_code,
        estimated_value_cad=request.estimated_value_cad,
        known_constraints=request.known_constraints,
        procurement_method=request.procurement_method,
    )

    # Persist session
    session_id = f"wb_{uuid.uuid4().hex}"
    session = WorkbenchSession(
        session_id=session_id,
        user_id=str(current_user.id),
        jurisdiction_code=request.jurisdiction_code,
        commodity_category_code=request.commodity_category_code,
        commodity_subcategory_code=request.commodity_subcategory_code,
        procurement_method=request.procurement_method,
        estimated_value_cad=request.estimated_value_cad,
        known_constraints=request.known_constraints,
        intent_description=request.intent_description,
        current_text=None,
        completeness_score=completeness,
        status="active",
        template_id=template_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    log_action(
        db,
        "WORKBENCH_SESSION_CREATED",
        {
            "session_id": session_id,
            "jurisdiction": request.jurisdiction_code,
            "commodity": request.commodity_category_code,
            "method": request.procurement_method,
        },
        user_id=str(current_user.id),
    )

    return {
        "session_id": session_id,
        "template_id": template_id,
        "sections": sections,
        "completeness_score": completeness,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# GET /session/{session_id}  (auth required)
# ---------------------------------------------------------------------------

@router.get("/session/{session_id}")
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return full state of an existing WorkbenchSession."""
    session = _get_session_or_404(session_id, db, current_user)

    # Reconstruct the sections list
    template_info = workbench_service.get_recommended_template(
        db=db,
        commodity_category_code=session.commodity_category_code,
        jurisdiction_code=session.jurisdiction_code,
        procurement_method=session.procurement_method,
    )

    return {
        "session_id": session.session_id,
        "jurisdiction_code": session.jurisdiction_code,
        "commodity_category_code": session.commodity_category_code,
        "commodity_subcategory_code": session.commodity_subcategory_code,
        "procurement_method": session.procurement_method,
        "estimated_value_cad": float(session.estimated_value_cad) if session.estimated_value_cad else None,
        "known_constraints": session.known_constraints or [],
        "intent_description": session.intent_description,
        "current_text": session.current_text,
        "completeness_score": session.completeness_score,
        "status": session.status,
        "template_id": session.template_id,
        "sections": template_info["sections"],
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# POST /guidance  (auth required)
# ---------------------------------------------------------------------------

@router.post("/guidance")
async def get_guidance(
    request: GuidanceRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Core intelligence endpoint — called when the user focuses on a new section.

    Returns real-time guidance notes, suggested language, clause recommendations,
    compliance warnings, and prompting questions from the AI.
    """
    session = _get_session_or_404(request.session_id, db, current_user)

    try:
        result = await workbench_service.generate_section_guidance(
            db=db,
            session=session,
            section_type=request.section_type,
            current_text=request.current_text,
        )
    except Exception as exc:
        logger.error("Guidance generation failed for session %s: %s", request.session_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Guidance generation failed. Please try again.")

    log_action(
        db,
        "WORKBENCH_GUIDANCE_REQUESTED",
        {"session_id": request.session_id, "section_type": request.section_type},
        user_id=str(current_user.id),
    )

    return result


# ---------------------------------------------------------------------------
# POST /draft-section  (auth required)
# ---------------------------------------------------------------------------

@router.post("/draft-section")
async def draft_section(
    request: SectionDraftRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate a full, professionally-worded section draft from the user's intent.

    The LLM is given: intent + jurisdiction + commodity + section_type +
    relevant mandatory knowledge articles.
    """
    session = _get_session_or_404(request.session_id, db, current_user)

    if not request.intent.strip():
        raise HTTPException(status_code=400, detail="intent must not be empty")

    try:
        result = await workbench_service.draft_section_text(
            db=db,
            session=session,
            section_type=request.section_type,
            intent=request.intent,
        )
    except Exception as exc:
        logger.error("Section draft failed for session %s: %s", request.session_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Section draft generation failed. Please try again.")

    log_action(
        db,
        "WORKBENCH_SECTION_DRAFTED",
        {
            "session_id": request.session_id,
            "section_type": request.section_type,
            "tokens_used": result.get("tokens_used", 0),
        },
        user_id=str(current_user.id),
    )

    return result


# ---------------------------------------------------------------------------
# POST /save  (auth required)
# ---------------------------------------------------------------------------

@router.post("/save")
def save_draft(
    request: SaveDraftRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Persist the current draft text and recalculate completeness score.
    """
    session = _get_session_or_404(request.session_id, db, current_user)

    # Reconstruct sections to drive completeness
    template_info = workbench_service.get_recommended_template(
        db=db,
        commodity_category_code=session.commodity_category_code,
        jurisdiction_code=session.jurisdiction_code,
        procurement_method=session.procurement_method,
    )
    sections = template_info["sections"]

    # Recalculate completeness from the saved text
    computed_score = workbench_service.calculate_completeness(request.current_text, sections)

    # If the caller provided an explicit score (e.g. from a prior LLM analysis), use it
    final_score = request.completeness_score if request.completeness_score is not None else computed_score

    # Determine missing sections (heuristic)
    text_lower = (request.current_text or "").lower()
    missing_sections = [
        s["section_type"]
        for s in sections
        if s["mandatory"] and s["section_type"] not in text_lower
    ]

    session.current_text = request.current_text
    session.completeness_score = final_score
    session.updated_at = datetime.utcnow()
    db.commit()

    log_action(
        db,
        "WORKBENCH_DRAFT_SAVED",
        {"session_id": request.session_id, "completeness_score": final_score},
        user_id=str(current_user.id),
    )

    return {
        "saved": True,
        "completeness_score": final_score,
        "missing_sections": missing_sections,
    }


# ---------------------------------------------------------------------------
# GET /evaluation-template  (auth required)
# ---------------------------------------------------------------------------

@router.get("/evaluation-template")
def get_evaluation_template(
    commodity_category_code: str = Query(...),
    jurisdiction_code: Optional[str] = Query(None),
    procurement_method: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return the best matching EvaluationTemplate for the given commodity /
    jurisdiction / method combination.

    Fallback order:
        1. Exact: category + jurisdiction + method
        2. Category + method
        3. Category only
        4. 404 if nothing found
    """
    cat = db.query(CommodityCategory).filter(
        CommodityCategory.code == commodity_category_code
    ).first()
    if not cat:
        raise HTTPException(status_code=422, detail=f"Unknown commodity_category_code: '{commodity_category_code}'")

    jur = None
    if jurisdiction_code:
        jur = db.query(Jurisdiction).filter(Jurisdiction.code == jurisdiction_code).first()

    tmpl: Optional[EvaluationTemplate] = None

    # Attempt 1: exact
    if jur and procurement_method:
        tmpl = (
            db.query(EvaluationTemplate)
            .filter(
                EvaluationTemplate.commodity_category_id == cat.id,
                EvaluationTemplate.jurisdiction_id == jur.id,
                EvaluationTemplate.procurement_method == procurement_method,
            )
            .first()
        )

    # Attempt 2: category + method
    if not tmpl and procurement_method:
        tmpl = (
            db.query(EvaluationTemplate)
            .filter(
                EvaluationTemplate.commodity_category_id == cat.id,
                EvaluationTemplate.procurement_method == procurement_method,
            )
            .first()
        )

    # Attempt 3: category only
    if not tmpl:
        tmpl = (
            db.query(EvaluationTemplate)
            .filter(EvaluationTemplate.commodity_category_id == cat.id)
            .first()
        )

    if not tmpl:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No evaluation template found for commodity '{commodity_category_code}'. "
                "Contact your procurement administrator to add one."
            ),
        )

    return {
        "template_id": tmpl.template_id,
        "criteria": tmpl.criteria or [],
        "award_methodology": tmpl.award_methodology,
        "award_methodology_template": tmpl.award_methodology_template or "",
        "cfta_disclosure_required": tmpl.cfta_disclosure_required,
    }


# ---------------------------------------------------------------------------
# GET /sla-template  (auth required)
# ---------------------------------------------------------------------------

@router.get("/sla-template")
def get_sla_template(
    commodity_category_code: str = Query(...),
    commodity_subcategory_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return the best matching SLATemplate.

    Fallback order:
        1. Category + subcategory
        2. Category only
        3. 404 if nothing found
    """
    cat = db.query(CommodityCategory).filter(
        CommodityCategory.code == commodity_category_code
    ).first()
    if not cat:
        raise HTTPException(status_code=422, detail=f"Unknown commodity_category_code: '{commodity_category_code}'")

    tmpl: Optional[SLATemplate] = None

    # Attempt 1: category + subcategory
    if commodity_subcategory_code:
        from app.models.commodity import CommoditySubcategory
        sub = db.query(CommoditySubcategory).filter(
            CommoditySubcategory.code == commodity_subcategory_code
        ).first()
        if sub:
            tmpl = (
                db.query(SLATemplate)
                .filter(
                    SLATemplate.commodity_category_id == cat.id,
                    SLATemplate.commodity_subcategory_id == sub.id,
                )
                .first()
            )

    # Attempt 2: category only
    if not tmpl:
        tmpl = (
            db.query(SLATemplate)
            .filter(SLATemplate.commodity_category_id == cat.id)
            .first()
        )

    if not tmpl:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No SLA template found for commodity '{commodity_category_code}'. "
                "Contact your procurement administrator to add one."
            ),
        )

    return {
        "template_id": tmpl.template_id,
        "kpis": tmpl.kpis or [],
        "reporting_cadence": tmpl.reporting_cadence,
    }


# ---------------------------------------------------------------------------
# POST /analyze-completeness  (auth required)
# ---------------------------------------------------------------------------

@router.post("/analyze-completeness")
async def analyze_completeness(
    request: SaveDraftRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Deep AI-powered completeness analysis of the current draft.

    Returns completeness score, completed/missing sections, obligation count,
    and specific risk flags.
    """
    session = _get_session_or_404(request.session_id, db, current_user)

    if not request.current_text or not request.current_text.strip():
        raise HTTPException(status_code=400, detail="current_text must not be empty")

    try:
        result = await workbench_service.analyze_completeness_with_llm(
            db=db,
            session=session,
            full_text=request.current_text,
        )
    except Exception as exc:
        logger.error(
            "Completeness analysis failed for session %s: %s",
            request.session_id, exc, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Completeness analysis failed. Please try again.")

    log_action(
        db,
        "WORKBENCH_COMPLETENESS_ANALYZED",
        {
            "session_id": request.session_id,
            "completeness_score": result.get("completeness_score"),
        },
        user_id=str(current_user.id),
    )

    return result


# ---------------------------------------------------------------------------
# POST /export  (auth required)
# ---------------------------------------------------------------------------

@router.post("/export")
def export_document(
    request: ExportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate the final formatted document from the session's current_text.

    Supported formats: "text" (plain) and "markdown".
    Returns: {document_text, format, word_count, section_count}
    """
    session = _get_session_or_404(request.session_id, db, current_user)

    if not session.current_text or not session.current_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Session has no draft text to export. Please save a draft first.",
        )

    if request.format not in ("text", "markdown"):
        raise HTTPException(
            status_code=422,
            detail="format must be 'text' or 'markdown'",
        )

    # Resolve display names for document header
    cat = db.query(CommodityCategory).filter(
        CommodityCategory.code == session.commodity_category_code
    ).first()
    jur = db.query(Jurisdiction).filter(
        Jurisdiction.code == session.jurisdiction_code
    ).first()

    commodity_name = cat.name if cat else session.commodity_category_code
    jurisdiction_name = jur.name if jur else session.jurisdiction_code

    now = datetime.utcnow().strftime("%Y-%m-%d")

    if request.format == "markdown":
        header = (
            f"# Statement of Work\n\n"
            f"**Jurisdiction:** {jurisdiction_name}  \n"
            f"**Commodity:** {commodity_name}  \n"
            f"**Procurement Method:** {session.procurement_method}  \n"
            f"**Draft Date:** {now}  \n"
            f"**Status:** {session.status.upper()}  \n\n"
            f"---\n\n"
        )
        document_text = header + session.current_text
    else:
        header = (
            f"STATEMENT OF WORK\n"
            f"{'=' * 60}\n"
            f"Jurisdiction      : {jurisdiction_name}\n"
            f"Commodity         : {commodity_name}\n"
            f"Procurement Method: {session.procurement_method}\n"
            f"Draft Date        : {now}\n"
            f"Status            : {session.status.upper()}\n"
            f"{'=' * 60}\n\n"
        )
        document_text = header + session.current_text

    word_count = len(document_text.split())
    # Count sections by looking for numbered headings or section_type keywords
    import re
    section_count = len(re.findall(r'^\s*\d+\.\s+', document_text, re.MULTILINE))
    if section_count == 0:
        # Fall back: count lines that look like headings (ALL CAPS or Title Case, ≤ 80 chars)
        section_count = len(re.findall(r'^[A-Z][A-Za-z &\-]+$', document_text, re.MULTILINE))

    # Mark session as exported
    session.status = "exported"
    session.updated_at = datetime.utcnow()
    db.commit()

    log_action(
        db,
        "WORKBENCH_SESSION_EXPORTED",
        {
            "session_id": request.session_id,
            "format": request.format,
            "word_count": word_count,
        },
        user_id=str(current_user.id),
    )

    return {
        "document_text": document_text,
        "format": request.format,
        "word_count": word_count,
        "section_count": section_count,
    }


# ---------------------------------------------------------------------------
# POST /session/{session_id}/extract-to-portfolio  (auth required)
# ---------------------------------------------------------------------------

@router.post("/session/{session_id}/extract-to-portfolio")
async def extract_session_to_portfolio(
    session_id: str,
    request: ExtractToPortfolioRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Bridge: take the session's drafted SOW text, create a draft
    PortfolioContract and run the LLM obligation extractor over the text.

    No obligations are persisted — the user reviews `proposals` and then
    calls /v1/portfolio/contracts/{contract_id}/obligations/batch-create
    to commit the ones they approve.
    """
    session = _get_session_or_404(session_id, db, current_user)

    sow_text = (session.current_text or "").strip()
    if not sow_text:
        raise HTTPException(
            status_code=400,
            detail="Session has no drafted text to extract from. Save a draft first.",
        )

    # Re-use the portfolio service helper rather than HTTP-calling ourselves.
    from app.routers.portfolio_routes import extract_and_stage_for_user

    result = await extract_and_stage_for_user(
        db=db,
        user=current_user,
        sow_text=sow_text,
        contract_type=request.contract_type,
        contract_name=request.contract_name,
        counterparty_name=request.counterparty_name,
        contract_value_cad=float(session.estimated_value_cad) if session.estimated_value_cad else None,
        jurisdiction_code=session.jurisdiction_code,
        our_role="buyer",
    )

    log_action(
        db,
        "WORKBENCH_EXTRACTED_TO_PORTFOLIO",
        {
            "session_id": session_id,
            "contract_id": result["contract"]["id"],
            "extracted_count": result["extracted_count"],
        },
        user_id=str(current_user.id),
    )

    return result
