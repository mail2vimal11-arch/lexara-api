"""
Procurement knowledge base models for the Lexara Workbench.

Contains:
    ProcurementFramework  — jurisdiction-level thresholds and rules
    KnowledgeArticle      — individual guidance clauses, templates, checklists
    SOWTemplate           — ordered section blueprints for SOW generation
    EvaluationTemplate    — evaluation plan blueprints with weighted criteria
    SLATemplate           — KPI / service-level blueprints
    WorkbenchSession      — per-user drafting session state
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    JSON,
    Numeric,
    DateTime,
    Date,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base


# ---------------------------------------------------------------------------
# ProcurementFramework
# ---------------------------------------------------------------------------


class ProcurementFramework(Base):
    """
    Jurisdiction-specific procurement rules: thresholds, allowed methods, and
    mandatory clause references.

    One jurisdiction can have multiple frameworks (e.g. goods vs. services
    policy instruments that are tracked separately), but typically one is
    current at a time.
    """

    __tablename__ = "procurement_frameworks"

    id = Column(Integer, primary_key=True, autoincrement=True)

    jurisdiction_id = Column(
        Integer,
        ForeignKey("jurisdictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    framework_name = Column(String(255), nullable=False)

    # Source document references
    legislation_ref = Column(String(500), nullable=True)
    policy_ref = Column(String(500), nullable=True)

    effective_date = Column(Date, nullable=True)

    # Domestic competitive thresholds (CAD) — below these, direct award is
    # permitted under the jurisdiction's own rules
    threshold_goods_cad = Column(Numeric(15, 2), nullable=True)
    threshold_services_cad = Column(Numeric(15, 2), nullable=True)
    threshold_construction_cad = Column(Numeric(15, 2), nullable=True)

    # CFTA (Canadian Free Trade Agreement) thresholds
    cfta_goods_threshold = Column(Numeric(15, 2), nullable=True)
    cfta_services_threshold = Column(Numeric(15, 2), nullable=True)
    cfta_construction_threshold = Column(Numeric(15, 2), nullable=True)

    # CUSMA (Canada-United States-Mexico Agreement) thresholds
    cusma_goods_threshold = Column(Numeric(15, 2), nullable=True)
    cusma_services_threshold = Column(Numeric(15, 2), nullable=True)

    # CETA (Comprehensive Economic and Trade Agreement) thresholds
    ceta_goods_threshold = Column(Numeric(15, 2), nullable=True)
    ceta_services_threshold = Column(Numeric(15, 2), nullable=True)

    # Procurement methods permitted under this framework
    # e.g. ["RFP", "RFQ", "ITT", "RFSO", "NPP", "LSA", "SOLE_SOURCE"]
    allowed_procurement_methods = Column(JSON, nullable=True)

    # Justification categories that permit sole-source award
    # e.g. ["NATIONAL_SECURITY", "ONLY_ONE_SUPPLIER", "EMERGENCY", "ADDITIONAL_WORK"]
    sole_source_grounds = Column(JSON, nullable=True)

    # Clause reference IDs that must appear in every contract under this framework
    mandatory_clauses = Column(JSON, nullable=True)

    notes = Column(Text, nullable=True)

    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    jurisdiction = relationship("Jurisdiction", back_populates="frameworks")

    def __repr__(self) -> str:
        return (
            f"<ProcurementFramework id={self.id} "
            f"jurisdiction_id={self.jurisdiction_id} "
            f"name={self.framework_name!r}>"
        )


# ---------------------------------------------------------------------------
# KnowledgeArticle
# ---------------------------------------------------------------------------


class KnowledgeArticle(Base):
    """
    Atomic unit of procurement knowledge — a clause, guidance note, template
    block, compliance check, SLA KPI definition, or evaluation criterion.

    Scoped by jurisdiction and/or commodity category; null FK means the
    article applies universally.

    article_type values:
        clause | scope_guidance | mandatory_req | rated_req |
        evaluation_criteria | sla_kpi | pricing_guidance |
        acceptance_criteria | risk_note | regulatory_requirement |
        template_language | compliance_check

    procurement_phase values:
        sow_drafting | solicitation | evaluation | award |
        contract_management | acceptance | closeout

    section_type values:
        background | scope | deliverables | mandatory_requirements |
        rated_requirements | pricing | evaluation_methodology |
        award_criteria | acceptance_criteria | sla | terms_conditions |
        transition
    """

    __tablename__ = "knowledge_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Human-readable stable ID used in template cross-references
    # e.g. "FED-IT-CLOUD-CLAUSE-DATA-RESIDENCY-001"
    article_id = Column(String(80), unique=True, nullable=False, index=True)

    # Scope — null FK = applies to all jurisdictions / all commodities
    jurisdiction_id = Column(
        Integer, ForeignKey("jurisdictions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    commodity_category_id = Column(
        Integer,
        ForeignKey("commodity_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    commodity_subcategory_id = Column(
        Integer,
        ForeignKey("commodity_subcategories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Classification
    article_type = Column(String(50), nullable=False)
    procurement_phase = Column(String(50), nullable=False)
    section_type = Column(String(60), nullable=False)

    # Content (bilingual)
    title = Column(String(255), nullable=False)
    title_fr = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    content_fr = Column(Text, nullable=True)

    # Ready-to-insert boilerplate with {PLACEHOLDER} tokens
    template_text = Column(Text, nullable=True)
    template_text_fr = Column(Text, nullable=True)

    # Advisory visible only to procurement officers
    guidance_note = Column(Text, nullable=True)

    # Source traceability
    # e.g. "SACC", "BPS_DIRECTIVE", "CFTA", "TB_POLICY", "ON_PROCUREMENT_ACT", "CUSTOM"
    source = Column(String(100), nullable=True)
    source_ref = Column(String(500), nullable=True)   # specific section / clause reference
    source_url = Column(String(500), nullable=True)

    # Applicability flags
    is_mandatory = Column(Boolean, nullable=False, default=False)

    # Importance: "critical" | "high" | "medium" | "low"
    importance = Column(String(20), nullable=False, default="medium")

    # Risk level if this article is omitted
    risk_if_omitted = Column(String(20), nullable=True)

    # Threshold gate — article only relevant above this contract value
    applies_above_value_cad = Column(Numeric(15, 2), nullable=True)

    # Procurement methods this article applies to; null = all methods
    # e.g. ["RFP", "RFSO"]
    applies_to_methods = Column(JSON, nullable=True)

    # Full-text search / faceting helpers
    tags = Column(JSON, nullable=True)

    # Cross-references to related article_ids
    related_article_ids = Column(JSON, nullable=True)

    # Versioning
    version = Column(String(20), nullable=False, default="1.0")
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    jurisdiction = relationship("Jurisdiction", back_populates="knowledge_articles")
    commodity_category = relationship("CommodityCategory", back_populates="knowledge_articles")
    commodity_subcategory = relationship(
        "CommoditySubcategory", back_populates="knowledge_articles"
    )

    def __repr__(self) -> str:
        return (
            f"<KnowledgeArticle article_id={self.article_id!r} "
            f"type={self.article_type!r} "
            f"importance={self.importance!r}>"
        )


# ---------------------------------------------------------------------------
# SOWTemplate
# ---------------------------------------------------------------------------


class SOWTemplate(Base):
    """
    Blueprint for generating a Statement of Work document.

    The `sections` JSON is an ordered list of section descriptors:
        [{
            "order": int,
            "section_type": str,       # maps to KnowledgeArticle.section_type
            "title": str,
            "mandatory": bool,
            "intelligence_mode": str,  # what the right-pane shows (e.g. "clause_list")
            "article_ids": [str],      # KnowledgeArticle.article_id references
            "placeholder_text": str    # default content when section starts empty
        }]

    The `completeness_checklist` JSON drives the top progress bar:
        [{"item": str, "required": bool, "description": str}]
    """

    __tablename__ = "sow_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Stable human-readable ID, e.g. "FED-IT-CLOUD-RFP-SOW-v1"
    template_id = Column(String(80), unique=True, nullable=False, index=True)

    # Scope — null FK = applies universally
    jurisdiction_id = Column(
        Integer, ForeignKey("jurisdictions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    commodity_category_id = Column(
        Integer,
        ForeignKey("commodity_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    commodity_subcategory_id = Column(
        Integer,
        ForeignKey("commodity_subcategories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # e.g. "RFP", "RFQ", "ITT", "RFSO"
    procurement_method = Column(String(20), nullable=False)

    # Ordered section list (see docstring above for schema)
    sections = Column(JSON, nullable=False, default=list)

    # Progress-bar checklist items
    completeness_checklist = Column(JSON, nullable=True)

    estimated_pages = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    version = Column(String(20), nullable=False, default="1.0")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    jurisdiction = relationship("Jurisdiction", back_populates="sow_templates")
    commodity_category = relationship("CommodityCategory", back_populates="sow_templates")
    commodity_subcategory = relationship("CommoditySubcategory", back_populates="sow_templates")

    def __repr__(self) -> str:
        return (
            f"<SOWTemplate template_id={self.template_id!r} "
            f"method={self.procurement_method!r} "
            f"version={self.version!r}>"
        )


# ---------------------------------------------------------------------------
# EvaluationTemplate
# ---------------------------------------------------------------------------


class EvaluationTemplate(Base):
    """
    Evaluation plan blueprint.

    award_methodology values:
        highest_combined_score | lowest_price_technically_acceptable |
        best_value | price_only

    The `criteria` JSON is a list of criterion descriptors:
        [{
            "id": str,
            "name": str,
            "criteria_type": str,          # "mandatory" | "rated" | "financial"
            "default_weight_pct": float,
            "max_points": int,
            "guidance": str,
            "sub_criteria": [{
                "name": str,
                "weight_pct": float,
                "max_points": int,
                "guidance": str
            }],
            "article_id": str              # linked KnowledgeArticle.article_id
        }]
    """

    __tablename__ = "evaluation_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)

    template_id = Column(String(80), unique=True, nullable=False, index=True)

    # Scope — null FK = applies universally
    jurisdiction_id = Column(
        Integer, ForeignKey("jurisdictions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    commodity_category_id = Column(
        Integer,
        ForeignKey("commodity_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)

    # e.g. "RFP", "ITT"
    procurement_method = Column(String(20), nullable=False)

    # Award methodology identifier (see docstring above)
    award_methodology = Column(String(50), nullable=False)

    # Ready-to-paste paragraph for insertion into solicitation document
    award_methodology_template = Column(Text, nullable=True)

    # Weighted criteria list (see docstring above for full schema)
    criteria = Column(JSON, nullable=False, default=list)

    # CFTA Article 509 requires disclosure of evaluation criteria and weights
    cfta_disclosure_required = Column(Boolean, nullable=False, default=True)

    # Notes on bid challenge exposure for this methodology
    bid_challenge_risk_note = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)
    version = Column(String(20), nullable=False, default="1.0")

    # Relationships
    jurisdiction = relationship("Jurisdiction", back_populates="evaluation_templates")
    commodity_category = relationship("CommodityCategory", back_populates="evaluation_templates")

    def __repr__(self) -> str:
        return (
            f"<EvaluationTemplate template_id={self.template_id!r} "
            f"methodology={self.award_methodology!r}>"
        )


# ---------------------------------------------------------------------------
# SLATemplate
# ---------------------------------------------------------------------------


class SLATemplate(Base):
    """
    Service Level Agreement / KPI blueprint for contract management.

    The `kpis` JSON is a list of KPI descriptors:
        [{
            "kpi_id": str,
            "name": str,
            "metric": str,
            "unit": str,
            "target_value": str,
            "measurement_method": str,
            "reporting_frequency": str,   # "daily"|"weekly"|"monthly"|"quarterly"
            "remedy_type": str,           # "service_credit"|"cure_period"|"termination_right"
            "remedy_formula": str,
            "article_id": str             # linked KnowledgeArticle.article_id
        }]
    """

    __tablename__ = "sla_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)

    template_id = Column(String(80), unique=True, nullable=False, index=True)

    # Commodity scope
    commodity_category_id = Column(
        Integer,
        ForeignKey("commodity_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    commodity_subcategory_id = Column(
        Integer,
        ForeignKey("commodity_subcategories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name = Column(String(255), nullable=False)

    # KPI list (see docstring above)
    kpis = Column(JSON, nullable=False, default=list)

    # e.g. "monthly", "quarterly"
    reporting_cadence = Column(String(50), nullable=True)

    # e.g. "annual", "semi-annual"
    review_frequency = Column(String(50), nullable=True)

    notes = Column(Text, nullable=True)
    version = Column(String(20), nullable=False, default="1.0")

    # Relationships
    commodity_category = relationship("CommodityCategory", back_populates="sla_templates")
    commodity_subcategory = relationship("CommoditySubcategory", back_populates="sla_templates")

    def __repr__(self) -> str:
        return f"<SLATemplate template_id={self.template_id!r} name={self.name!r}>"


# ---------------------------------------------------------------------------
# WorkbenchSession
# ---------------------------------------------------------------------------


class WorkbenchSession(Base):
    """
    Persisted state for a single Lexara Workbench drafting session.

    One session corresponds to one procurement requirement being drafted by
    one user.  The session is created at intake, updated as the user drafts,
    and marked "exported" or "archived" on completion.

    status values: "active" | "exported" | "archived"
    """

    __tablename__ = "workbench_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Externally surfaced session identifier (UUID string)
    session_id = Column(String(50), unique=True, nullable=False, index=True)

    # References users.id (String UUID PK in User model) — soft FK, no cascade
    user_id = Column(String(50), nullable=True, index=True)

    # Intake selections — stored as codes for portability
    jurisdiction_code = Column(String(10), nullable=False)
    commodity_category_code = Column(String(50), nullable=False)
    commodity_subcategory_code = Column(String(60), nullable=True)
    procurement_method = Column(String(20), nullable=False)

    # Estimated contract value in CAD — drives threshold logic
    estimated_value_cad = Column(Numeric(15, 2), nullable=True)

    # Active constraint flags selected at intake
    # e.g. ["SECURITY_CLEARANCE", "BILINGUAL", "INDIGENOUS_SET_ASIDE"]
    known_constraints = Column(JSON, nullable=True)

    # Free-text requirement description entered at intake
    intent_description = Column(Text, nullable=True)

    # The SOW document being drafted — saved periodically (auto-save)
    current_text = Column(Text, nullable=True)

    # 0.0–1.0 completeness score computed from completeness_checklist
    completeness_score = Column(Float, nullable=True)

    # Lifecycle status
    status = Column(String(20), nullable=False, default="active")

    # Soft reference to SOWTemplate.template_id applied to this session
    template_id = Column(String(80), nullable=True, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<WorkbenchSession session_id={self.session_id!r} "
            f"status={self.status!r} "
            f"jurisdiction={self.jurisdiction_code!r} "
            f"commodity={self.commodity_category_code!r}>"
        )
