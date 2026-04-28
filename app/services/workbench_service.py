"""
Workbench service — SOW drafting intelligence layer.
"""
import logging
import json
import re
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeArticle, SOWTemplate, EvaluationTemplate, SLATemplate, WorkbenchSession
from app.models.commodity import CommodityCategory
from app.models.jurisdiction import Jurisdiction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default template fallback
# ---------------------------------------------------------------------------

DEFAULT_SECTIONS = [
    {"order": 1, "section_type": "background", "title": "1. Background & Context", "mandatory": True, "intelligence_mode": "background_guidance"},
    {"order": 2, "section_type": "scope", "title": "2. Scope of Work", "mandatory": True, "intelligence_mode": "scope_guidance"},
    {"order": 3, "section_type": "deliverables", "title": "3. Deliverables & Milestones", "mandatory": True, "intelligence_mode": "deliverables_guidance"},
    {"order": 4, "section_type": "mandatory_requirements", "title": "4. Mandatory Requirements", "mandatory": True, "intelligence_mode": "mandatory_req_guidance"},
    {"order": 5, "section_type": "rated_requirements", "title": "5. Rated Requirements", "mandatory": False, "intelligence_mode": "rated_req_guidance"},
    {"order": 6, "section_type": "pricing", "title": "6. Pricing Schedule", "mandatory": True, "intelligence_mode": "pricing_guidance"},
    {"order": 7, "section_type": "evaluation_methodology", "title": "7. Evaluation & Award Methodology", "mandatory": True, "intelligence_mode": "evaluation_guidance"},
    {"order": 8, "section_type": "acceptance_criteria", "title": "8. Acceptance Criteria", "mandatory": True, "intelligence_mode": "acceptance_guidance"},
    {"order": 9, "section_type": "sla", "title": "9. Performance Standards & SLA", "mandatory": False, "intelligence_mode": "sla_guidance"},
    {"order": 10, "section_type": "terms_conditions", "title": "10. Contract Terms & Conditions", "mandatory": True, "intelligence_mode": "terms_guidance"},
    {"order": 11, "section_type": "transition", "title": "11. Transition-In & Transition-Out", "mandatory": False, "intelligence_mode": "transition_guidance"},
]

# CFTA thresholds by commodity type prefix (CAD)
CFTA_GOODS_THRESHOLD = 33_400.0
CFTA_SERVICES_THRESHOLD = 121_200.0
CFTA_CONSTRUCTION_THRESHOLD = 7_800_000.0

# Importance ordering for sort key
IMPORTANCE_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ---------------------------------------------------------------------------
# get_recommended_template
# ---------------------------------------------------------------------------

def get_recommended_template(
    db: Session,
    commodity_category_code: str,
    jurisdiction_code: str,
    procurement_method: str,
) -> Optional[dict]:
    """
    Return the best-matching SOWTemplate as a plain dict.

    Lookup priority:
        1. Exact match: commodity_category + jurisdiction + procurement_method
        2. Category + procurement_method (any jurisdiction)
        3. Category only (any jurisdiction, any method)
        4. Built-in default template structure

    Returns a dict with keys: template_id, name, sections, completeness_checklist
    """
    # Resolve commodity category DB row
    cat = db.query(CommodityCategory).filter(
        CommodityCategory.code == commodity_category_code
    ).first()

    if cat is None:
        logger.warning(
            "get_recommended_template: unknown commodity_category_code %r — using default",
            commodity_category_code,
        )
        return _default_template_dict(commodity_category_code, procurement_method)

    # Resolve jurisdiction DB row (may be None — that's fine)
    jur = db.query(Jurisdiction).filter(
        Jurisdiction.code == jurisdiction_code
    ).first()

    # Attempt 1: exact match including jurisdiction
    if jur:
        tmpl = (
            db.query(SOWTemplate)
            .filter(
                SOWTemplate.commodity_category_id == cat.id,
                SOWTemplate.jurisdiction_id == jur.id,
                SOWTemplate.procurement_method == procurement_method,
            )
            .first()
        )
        if tmpl:
            return _template_to_dict(tmpl)

    # Attempt 2: category + method, no jurisdiction constraint
    tmpl = (
        db.query(SOWTemplate)
        .filter(
            SOWTemplate.commodity_category_id == cat.id,
            SOWTemplate.procurement_method == procurement_method,
        )
        .first()
    )
    if tmpl:
        return _template_to_dict(tmpl)

    # Attempt 3: category only
    tmpl = (
        db.query(SOWTemplate)
        .filter(SOWTemplate.commodity_category_id == cat.id)
        .first()
    )
    if tmpl:
        return _template_to_dict(tmpl)

    # Attempt 4: built-in default
    return _default_template_dict(commodity_category_code, procurement_method)


def _template_to_dict(tmpl: SOWTemplate) -> dict:
    return {
        "template_id": tmpl.template_id,
        "name": tmpl.name,
        "sections": tmpl.sections or DEFAULT_SECTIONS,
        "completeness_checklist": tmpl.completeness_checklist or [],
    }


def _default_template_dict(commodity_category_code: str, procurement_method: str) -> dict:
    return {
        "template_id": f"DEFAULT-{commodity_category_code}-{procurement_method}",
        "name": f"Default {procurement_method} SOW Template",
        "sections": DEFAULT_SECTIONS,
        "completeness_checklist": [],
    }


# ---------------------------------------------------------------------------
# get_knowledge_for_section
# ---------------------------------------------------------------------------

def get_knowledge_for_section(
    db: Session,
    section_type: str,
    commodity_category_code: str,
    jurisdiction_code: str,
    limit: int = 8,
) -> List[dict]:
    """
    Return knowledge articles relevant to a given SOW section.

    Filters:
        - section_type matches exactly
        - commodity_category_id == category.id  OR  commodity_category_id IS NULL
        - jurisdiction_id == jurisdiction.id     OR  jurisdiction_id IS NULL

    Ordering: mandatory first, then by importance (critical → high → medium → low).
    Returns at most `limit` results as plain dicts.
    """
    cat = db.query(CommodityCategory).filter(
        CommodityCategory.code == commodity_category_code
    ).first()

    jur = db.query(Jurisdiction).filter(
        Jurisdiction.code == jurisdiction_code
    ).first()

    q = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.section_type == section_type,
        KnowledgeArticle.is_active == True,  # noqa: E712
    )

    # Commodity filter: match category OR universal (NULL)
    if cat:
        from sqlalchemy import or_
        q = q.filter(
            or_(
                KnowledgeArticle.commodity_category_id == cat.id,
                KnowledgeArticle.commodity_category_id == None,  # noqa: E711
            )
        )
    else:
        q = q.filter(KnowledgeArticle.commodity_category_id == None)  # noqa: E711

    # Jurisdiction filter: match jurisdiction OR universal (NULL)
    if jur:
        from sqlalchemy import or_
        q = q.filter(
            or_(
                KnowledgeArticle.jurisdiction_id == jur.id,
                KnowledgeArticle.jurisdiction_id == None,  # noqa: E711
            )
        )
    else:
        q = q.filter(KnowledgeArticle.jurisdiction_id == None)  # noqa: E711

    articles = q.all()

    # Sort: mandatory first, then by importance
    articles.sort(
        key=lambda a: (
            0 if a.is_mandatory else 1,
            IMPORTANCE_ORDER.get(a.importance or "medium", 2),
        )
    )

    return [
        {
            "article_id": a.article_id,
            "title": a.title,
            "content": a.content,
            "template_text": a.template_text,
            "guidance_note": a.guidance_note,
            "is_mandatory": a.is_mandatory,
            "importance": a.importance,
            "source": a.source,
        }
        for a in articles[:limit]
    ]


# ---------------------------------------------------------------------------
# generate_section_guidance
# ---------------------------------------------------------------------------

async def generate_section_guidance(
    db: Session,
    session: WorkbenchSession,
    section_type: str,
    current_text: str,
) -> dict:
    """
    Core intelligence: produce real-time guidance when the user focuses on a
    SOW section.

    Returns:
        guidance_notes        — knowledge articles rendered as advisory cards
        suggested_language    — LLM-generated opening text for the section
        clause_recommendations — knowledge articles with template_text
        warnings              — constraint/compliance warnings for this section
        prompting_questions   — LLM-generated questions to help the user
    """
    from app.services.llm_service import analyze_with_claude

    # 1. Pull knowledge articles
    articles = get_knowledge_for_section(
        db,
        section_type=section_type,
        commodity_category_code=session.commodity_category_code,
        jurisdiction_code=session.jurisdiction_code,
        limit=8,
    )

    # 2. Resolve display names for the prompt
    cat = db.query(CommodityCategory).filter(
        CommodityCategory.code == session.commodity_category_code
    ).first()
    jur = db.query(Jurisdiction).filter(
        Jurisdiction.code == session.jurisdiction_code
    ).first()

    commodity_name = cat.name if cat else session.commodity_category_code
    jurisdiction_name = jur.name if jur else session.jurisdiction_code

    # 3. Build guidance prompt
    truncated_text = (current_text or "")[:500]
    prompt = (
        f"You are a senior Canadian procurement advisor helping draft a {section_type} section "
        f"for a {commodity_name} {session.procurement_method} under {jurisdiction_name} law.\n\n"
        f"The procurement professional has typed so far:\n"
        f'"{truncated_text if truncated_text else "Nothing yet."}"\n\n'
        f"Based on this section type and commodity, provide:\n"
        f"1. Three specific prompting questions to help them articulate what's needed\n"
        f"2. Suggested opening language for this section (2-3 sentences)\n"
        f"3. Three key topics they must address in this section\n\n"
        f"Return JSON:\n"
        f'{{\n'
        f'  "prompting_questions": ["Q1", "Q2", "Q3"],\n'
        f'  "suggested_opening": "...",\n'
        f'  "key_topics": ["Topic 1", "Topic 2", "Topic 3"]\n'
        f'}}'
    )

    # 4. Call LLM — use a stub-safe wrapper (mode="workbench_guidance")
    llm_result = {}
    try:
        llm_result = await analyze_with_claude(
            text=prompt,
            contract_type="SOW",
            jurisdiction=session.jurisdiction_code,
            mode="workbench_guidance",
        )
    except Exception as exc:
        logger.warning("LLM call failed for section guidance: %s", exc)
        llm_result = {}

    # 5. Assemble clause recommendations (articles that have template_text)
    clause_recommendations = [
        {
            "article_id": a["article_id"],
            "title": a["title"],
            "template_text": a["template_text"] or "",
            "is_mandatory": a["is_mandatory"],
        }
        for a in articles
        if a.get("template_text")
    ]

    # 6. Guidance notes (all articles, displayed as advisory cards)
    guidance_notes = [
        {
            "title": a["title"],
            "content": a["content"],
            "importance": a["importance"],
            "source": a["source"] or "Lexara Knowledge Base",
        }
        for a in articles
    ]

    # 7. Section-level warnings derived from session constraints
    warnings = _section_warnings(
        section_type=section_type,
        jurisdiction_code=session.jurisdiction_code,
        known_constraints=session.known_constraints or [],
        procurement_method=session.procurement_method,
    )

    return {
        "guidance_notes": guidance_notes,
        "suggested_language": llm_result.get("suggested_opening", ""),
        "clause_recommendations": clause_recommendations,
        "warnings": warnings,
        "prompting_questions": llm_result.get("prompting_questions", []),
    }


# ---------------------------------------------------------------------------
# draft_section_text
# ---------------------------------------------------------------------------

async def draft_section_text(
    db: Session,
    session: WorkbenchSession,
    section_type: str,
    intent: str,
) -> dict:
    """
    Generate a full professionally-worded SOW section draft from the user's
    intent description plus jurisdiction/commodity context.

    Returns: {drafted_text, clauses_used, tokens_used}
    """
    from app.services.llm_service import analyze_with_claude

    # Resolve display names
    cat = db.query(CommodityCategory).filter(
        CommodityCategory.code == session.commodity_category_code
    ).first()
    jur = db.query(Jurisdiction).filter(
        Jurisdiction.code == session.jurisdiction_code
    ).first()

    commodity_name = cat.name if cat else session.commodity_category_code
    jurisdiction_name = jur.name if jur else session.jurisdiction_code

    # Fetch mandatory articles and build clause context
    articles = get_knowledge_for_section(
        db,
        section_type=section_type,
        commodity_category_code=session.commodity_category_code,
        jurisdiction_code=session.jurisdiction_code,
        limit=6,
    )

    mandatory_clause_snippets = []
    clauses_used = []
    for a in articles:
        if a["is_mandatory"] and a.get("template_text"):
            mandatory_clause_snippets.append(
                f"[MANDATORY — {a['source'] or 'Policy'}] {a['title']}:\n{a['template_text']}"
            )
            clauses_used.append(a["article_id"])

    clause_context = (
        "\n\n".join(mandatory_clause_snippets)
        if mandatory_clause_snippets
        else "No mandatory clause templates on record for this section/commodity combination."
    )

    # Jurisdiction flags
    bilingual_note = ""
    if jur and jur.requires_bilingual:
        bilingual_note = (
            "NOTE: This jurisdiction requires bilingual documents under the Official Languages Act. "
            "Draft section headings and key terms bilingually where applicable."
        )

    trade_note = ""
    if jur and jur.trade_agreements:
        agreements = ", ".join(jur.trade_agreements)
        trade_note = f"Applicable trade agreements: {agreements}."

    prompt = (
        f"You are a senior Canadian government procurement specialist. "
        f"Draft a complete, professionally-worded {section_type} section for a "
        f"{session.procurement_method} Statement of Work.\n\n"
        f"PROCUREMENT CONTEXT\n"
        f"  Jurisdiction : {jurisdiction_name} ({session.jurisdiction_code})\n"
        f"  Commodity    : {commodity_name} ({session.commodity_category_code})\n"
        f"  Method       : {session.procurement_method}\n"
        f"  Estimated value (CAD): {session.estimated_value_cad or 'Not specified'}\n"
        f"  Constraints  : {', '.join(session.known_constraints or []) or 'None'}\n"
        f"  {trade_note}\n"
        f"  {bilingual_note}\n\n"
        f"USER INTENT\n"
        f'"{intent}"\n\n'
        f"MANDATORY CLAUSES TO INCORPORATE\n"
        f"{clause_context}\n\n"
        f"INSTRUCTIONS\n"
        f"1. Write the section in formal Canadian government procurement language.\n"
        f"2. Use 'the Contractor shall' / 'the Contractor must' for obligations.\n"
        f"3. Include all mandatory clauses above verbatim or adapted to context.\n"
        f"4. Use numbered sub-clauses.\n"
        f"5. Do not add a section number prefix — the caller will add it.\n\n"
        f"Return JSON:\n"
        f'{{\n'
        f'  "drafted_text": "full section text here",\n'
        f'  "clauses_used": ["article_id_1", "article_id_2"]\n'
        f'}}'
    )

    tokens_used = 0
    drafted_text = ""
    try:
        result = await analyze_with_claude(
            text=prompt,
            contract_type="SOW",
            jurisdiction=session.jurisdiction_code,
            mode="draft_section",
        )
        drafted_text = result.get("drafted_text", "")
        # LLM may return its own clause list; merge with ours
        llm_clauses = result.get("clauses_used", [])
        all_clauses = list(set(clauses_used + [c for c in llm_clauses if isinstance(c, str)]))
        tokens_used = result.get("tokens_used", 0)
    except Exception as exc:
        logger.error("draft_section_text LLM call failed: %s", exc)
        drafted_text = (
            f"[Draft generation failed — please try again. Error: {exc}]\n\n"
            f"Your intent: {intent}"
        )
        all_clauses = clauses_used

    return {
        "drafted_text": drafted_text,
        "clauses_used": all_clauses,
        "tokens_used": tokens_used,
    }


# ---------------------------------------------------------------------------
# calculate_completeness
# ---------------------------------------------------------------------------

def calculate_completeness(current_text: str, sections: list) -> float:
    """
    Heuristic completeness score (0–100).

    A section is considered "present" if the text contains at least one of
    the section's keywords OR the section title substring.  Mandatory sections
    count double toward the score.

    Returns a float in [0.0, 100.0].
    """
    if not current_text or not sections:
        return 0.0

    text_lower = current_text.lower()

    # Keywords associated with each section_type
    SECTION_KEYWORDS: Dict[str, List[str]] = {
        "background": ["background", "context", "overview", "introduction", "about the"],
        "scope": ["scope of work", "scope", "in scope", "out of scope", "activities"],
        "deliverables": ["deliverable", "milestone", "work package", "output", "artifact"],
        "mandatory_requirements": ["mandatory", "must", "required", "shall", "requirement"],
        "rated_requirements": ["rated", "point", "criteria", "score", "assessed"],
        "pricing": ["pricing", "price", "cost", "rate", "fee", "schedule", "invoic"],
        "evaluation_methodology": ["evaluation", "award", "methodology", "selection"],
        "acceptance_criteria": ["acceptance", "accepted", "approved", "sign-off", "sign off"],
        "sla": ["service level", "sla", "kpi", "performance standard", "metric"],
        "terms_conditions": ["terms", "condition", "termination", "liability", "governing law"],
        "transition": ["transition", "handover", "knowledge transfer", "incumbent"],
    }

    total_weight = 0.0
    achieved_weight = 0.0

    for section in sections:
        stype = section.get("section_type", "")
        is_mandatory = section.get("mandatory", False)
        weight = 2.0 if is_mandatory else 1.0
        total_weight += weight

        keywords = SECTION_KEYWORDS.get(stype, [])
        title_fragment = section.get("title", "").lower()

        # Check title substring
        present = title_fragment and title_fragment in text_lower

        # Check keywords
        if not present:
            for kw in keywords:
                if kw in text_lower:
                    present = True
                    break

        if present:
            achieved_weight += weight

    if total_weight == 0:
        return 0.0

    score = (achieved_weight / total_weight) * 100.0
    return round(min(score, 100.0), 1)


# ---------------------------------------------------------------------------
# analyze_completeness_with_llm
# ---------------------------------------------------------------------------

async def analyze_completeness_with_llm(
    db: Session,
    session: WorkbenchSession,
    full_text: str,
) -> dict:
    """
    Deep completeness analysis via LLM.

    Returns:
        completeness_score   float  0-100
        completed_sections   list[str]
        missing_sections     list[{section_type, importance, description}]
        obligation_count     int
        risk_flags           list[{flag, severity, recommendation}]
    """
    from app.services.llm_service import analyze_with_claude

    # Resolve display names
    cat = db.query(CommodityCategory).filter(
        CommodityCategory.code == session.commodity_category_code
    ).first()
    jur = db.query(Jurisdiction).filter(
        Jurisdiction.code == session.jurisdiction_code
    ).first()

    commodity_name = cat.name if cat else session.commodity_category_code
    jurisdiction_name = jur.name if jur else session.jurisdiction_code

    # Quick obligation count (heuristic, always available)
    obligation_count = _count_obligations(full_text)

    # Heuristic completeness as a fallback / cross-check
    heuristic_score = calculate_completeness(full_text, DEFAULT_SECTIONS)

    prompt = (
        f"You are a Canadian government procurement expert reviewing a draft Statement of Work.\n\n"
        f"CONTEXT\n"
        f"  Jurisdiction : {jurisdiction_name}\n"
        f"  Commodity    : {commodity_name}\n"
        f"  Method       : {session.procurement_method}\n\n"
        f"DRAFT SOW (up to 8000 chars):\n"
        f"{full_text[:8000]}\n\n"
        f"Analyze the draft for completeness. The expected sections are:\n"
        f"{', '.join(s['section_type'] for s in DEFAULT_SECTIONS)}\n\n"
        f"Return JSON exactly:\n"
        f'{{\n'
        f'  "completeness_score": 0-100,\n'
        f'  "completed_sections": ["section_type_1", ...],\n'
        f'  "missing_sections": [\n'
        f'    {{"section_type": "...", "importance": "critical|high|medium|low", "description": "why it is needed"}}\n'
        f'  ],\n'
        f'  "risk_flags": [\n'
        f'    {{"flag": "...", "severity": "critical|high|medium|low", "recommendation": "..."}}\n'
        f'  ]\n'
        f'}}'
    )

    try:
        result = await analyze_with_claude(
            text=prompt,
            contract_type="SOW",
            jurisdiction=session.jurisdiction_code,
            mode="completeness_analysis",
        )
        return {
            "completeness_score": result.get("completeness_score", heuristic_score),
            "completed_sections": result.get("completed_sections", []),
            "missing_sections": result.get("missing_sections", []),
            "obligation_count": obligation_count,
            "risk_flags": result.get("risk_flags", []),
        }
    except Exception as exc:
        logger.error("analyze_completeness_with_llm failed: %s", exc)
        # Graceful degradation: return heuristic data
        present_sections = [
            s["section_type"]
            for s in DEFAULT_SECTIONS
            if s["section_type"].lower() in (full_text or "").lower()
        ]
        missing_sections = [
            {
                "section_type": s["section_type"],
                "importance": "critical" if s["mandatory"] else "medium",
                "description": f"{s['title']} section appears to be absent from the draft.",
            }
            for s in DEFAULT_SECTIONS
            if s["section_type"] not in present_sections
        ]
        return {
            "completeness_score": heuristic_score,
            "completed_sections": present_sections,
            "missing_sections": missing_sections,
            "obligation_count": obligation_count,
            "risk_flags": [],
        }


# ---------------------------------------------------------------------------
# generate_warnings
# ---------------------------------------------------------------------------

def generate_warnings(
    jurisdiction_code: str,
    commodity_category_code: str,
    estimated_value_cad: Optional[float],
    known_constraints: list,
    procurement_method: str,
) -> list:
    """
    Rule-based warnings generated at session creation time.

    Returns a list of plain warning strings.
    """
    warnings: List[str] = []

    value = estimated_value_cad or 0.0

    # ── CFTA threshold detection ──────────────────────────────────────────
    if commodity_category_code.startswith("CON_"):
        cfta_threshold = CFTA_CONSTRUCTION_THRESHOLD
    elif commodity_category_code.startswith("GOODS_") or commodity_category_code.startswith("IT_HW"):
        cfta_threshold = CFTA_GOODS_THRESHOLD
    else:
        cfta_threshold = CFTA_SERVICES_THRESHOLD

    if value > cfta_threshold:
        warnings.append(
            "CFTA applies. Evaluation criteria and weights must be disclosed in the solicitation "
            "(CFTA Article 509). Ensure the evaluation methodology section is complete before posting."
        )

    # ── Official Languages Act ────────────────────────────────────────────
    if "BILINGUAL" in known_constraints or jurisdiction_code == "FED":
        warnings.append(
            "Official Languages Act requires bilingual solicitation document. "
            "All mandatory headings, instructions, and evaluation criteria must appear "
            "in both English and French."
        )

    # ── Indigenous procurement ────────────────────────────────────────────
    if "INDIGENOUS_SET_ASIDE" in known_constraints:
        warnings.append(
            "Procurement for Indigenous Business (PSIB) / indigenous set-aside policy applies. "
            "Ensure set-aside justification is documented and the eligible-bidder definition "
            "complies with the Indigenous Business Directory criteria."
        )

    # ── Ontario Prompt Payment Act ────────────────────────────────────────
    if jurisdiction_code == "ON" and commodity_category_code.startswith("CON_"):
        warnings.append(
            "Ontario Prompt Payment Act (Construction) applies to this contract. "
            "Include prompt payment milestones, proper invoice timelines (28 days), "
            "and adjudication rights in the terms & conditions section."
        )

    # ── Sole-source justification ─────────────────────────────────────────
    if procurement_method == "SOLE_SOURCE":
        warnings.append(
            "Document sole-source justification before posting. CFTA Article 504 "
            "exceptions apply. Retain justification records for audit purposes."
        )

    # ── Security clearance ────────────────────────────────────────────────
    if "SECURITY_CLEARANCE" in known_constraints:
        warnings.append(
            "Security clearance requirement detected. Include mandatory security screening "
            "clause (TBITS / TBS Standard) in the Mandatory Requirements section. "
            "Specify clearance level (Reliability, Secret, Top Secret) explicitly."
        )

    # ── AODA / accessibility ──────────────────────────────────────────────
    if "AODA" in known_constraints or jurisdiction_code == "ON":
        warnings.append(
            "Accessibility for Ontarians with Disabilities Act (AODA) may apply. "
            "Deliverables that include digital content or software must meet WCAG 2.1 AA."
        )

    return warnings


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _count_obligations(text: str) -> int:
    """Count binding obligation keywords (shall, must, will) in the text."""
    if not text:
        return 0
    pattern = re.compile(r'\b(shall|must|will)\b', re.IGNORECASE)
    return len(pattern.findall(text))


def _section_warnings(
    section_type: str,
    jurisdiction_code: str,
    known_constraints: list,
    procurement_method: str,
) -> List[str]:
    """Return section-specific compliance warnings."""
    warnings: List[str] = []

    if section_type == "evaluation_methodology":
        warnings.append(
            "CFTA Article 509: Evaluation criteria and their relative weights must be "
            "disclosed in the solicitation at time of posting."
        )

    if section_type == "mandatory_requirements" and "SECURITY_CLEARANCE" in known_constraints:
        warnings.append(
            "This section must include a mandatory security screening clause "
            "specifying the required clearance level."
        )

    if section_type in ("background", "scope") and "BILINGUAL" in known_constraints:
        warnings.append(
            "Official Languages Act: Ensure this section appears in both English and French."
        )

    if section_type == "terms_conditions" and jurisdiction_code == "ON":
        warnings.append(
            "Ontario Prompt Payment Act: Include payment timelines and adjudication rights."
        )

    if section_type == "pricing" and procurement_method == "RFSO":
        warnings.append(
            "RFSO: Pricing schedule must be based on a rate card or ceiling rate. "
            "Avoid fixed-price lump sums in standing offer instruments."
        )

    return warnings
