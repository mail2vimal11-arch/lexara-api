"""
Negotiation models for the Lexara Clause Negotiation Simulator.

Contains:
    NegotiationSession    — top-level session tracking a full contract negotiation
    NegotiationClause     — one clause being negotiated per session
    NegotiationRound      — one proposal/response move per clause per turn
    NegotiationConcession — running ledger of concessions gave/gained
    JurisprudenceArticle  — Canadian case law and CITT decisions indexed by clause type
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
    Float,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base


# ---------------------------------------------------------------------------
# NegotiationSession
# ---------------------------------------------------------------------------


class NegotiationSession(Base):
    """
    Top-level record for one contract negotiation session.

    party_type values:
        government_authority | federal_vendor | provincial_vendor |
        prime_contractor | subcontractor | software_licensor |
        software_licensee | employer | employee |
        commercial_buyer | commercial_seller

    status values:
        intake | active | stalemate | agreed | exported | abandoned
    """

    __tablename__ = "negotiation_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Externally surfaced identifier, e.g. "neg_abc123def456"
    session_id = Column(String(50), unique=True, nullable=False, index=True)

    # Soft FK to users.id — String UUID PK in User model
    user_id = Column(String(50), nullable=True, index=True)

    # Which side of the table the user is sitting on
    party_type = Column(String(50), nullable=False)

    # Canadian jurisdiction code, e.g. "ON", "FED", "BC"
    jurisdiction_code = Column(String(10), nullable=False)

    # Commodity category from the procurement knowledge base
    commodity_category_code = Column(String(50), nullable=True)

    # Estimated contract value in CAD
    contract_value_cad = Column(Numeric(15, 2), nullable=True)

    # Market concentration proxy:
    #   1 = sole source, 2-3, 4-10, 11 = 10+
    vendor_count_estimate = Column(Integer, nullable=True)

    # True if the fiscal quarter end is approaching (increases time pressure)
    fiscal_quarter_end_pressure = Column(Boolean, default=False, nullable=False)

    # Full contract text pasted in by the user
    original_contract_text = Column(Text, nullable=True)

    # Clause keys the user declared as must-have (JSON list of strings)
    non_negotiables = Column(JSON, nullable=True)

    # Clause keys the user is willing to trade (JSON list of strings)
    tradeable_items = Column(JSON, nullable=True)

    # AI-inferred mirror role for the opposing party
    opposing_party_type = Column(String(50), nullable=True)

    # BATNA scores 0-100, updated each round
    batna_score = Column(Float, nullable=True)
    batna_score_opponent = Column(Float, nullable=True)

    # Running financial outcome totals
    total_risk_reduction_cad = Column(Numeric(15, 2), nullable=True, default=0)
    total_concessions_cad = Column(Numeric(15, 2), nullable=True, default=0)

    # How many full proposal/response cycles have been completed
    rounds_completed = Column(Integer, default=0, nullable=False)

    # Lifecycle status
    status = Column(String(20), default="intake", nullable=False)

    # Multi-party / opposing-counsel invite
    multi_party_token = Column(String(100), unique=True, nullable=True, index=True)
    multi_party_opponent_user_id = Column(String(50), nullable=True)
    invite_expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    clauses = relationship(
        "NegotiationClause",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="NegotiationClause.display_order",
    )
    rounds = relationship(
        "NegotiationRound",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="NegotiationRound.id",
    )

    def __repr__(self) -> str:
        return (
            f"<NegotiationSession id={self.id} "
            f"session_id={self.session_id!r} "
            f"party_type={self.party_type!r} "
            f"status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# NegotiationClause
# ---------------------------------------------------------------------------


class NegotiationClause(Base):
    """
    One clause being negotiated within a NegotiationSession.

    state values:
        pending | your_move | opponent_move | agreed |
        stalemate | trade_pending | withdrawn

    clause_type values:
        liability | ip | termination | payment | indemnification |
        warranty | sla | confidentiality | acceptance | governing_law

    risk_severity values:
        critical | high | medium | low
    """

    __tablename__ = "negotiation_clauses"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # FK to the parent session
    session_id = Column(
        Integer,
        ForeignKey("negotiation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Machine-readable key, unique within a session, e.g. "liability_cap"
    clause_key = Column(String(100), nullable=False)

    # Human-readable display label
    clause_title = Column(String(255), nullable=False)

    # The verbatim text extracted from the uploaded contract
    original_text = Column(Text, nullable=False)

    # The user's current revision proposal
    your_proposed_text = Column(Text, nullable=True)

    # The AI opponent's current revision proposal
    opponent_proposed_text = Column(Text, nullable=True)

    # Final text once both sides have agreed
    agreed_text = Column(Text, nullable=True)

    # Negotiation state machine
    state = Column(String(30), default="pending", nullable=False)

    # Flags set from the intake request
    is_user_non_negotiable = Column(Boolean, default=False, nullable=False)
    is_user_tradeable = Column(Boolean, default=False, nullable=False)

    # Risk classification
    risk_severity = Column(String(20), nullable=True)

    # Estimated CAD exposure if this clause is left unchanged
    risk_exposure_cad = Column(Numeric(15, 2), nullable=True)

    # CAD value saved once the clause is agreed in the user's favour
    risk_reduction_achieved_cad = Column(Numeric(15, 2), nullable=True)

    # Semantic clause category
    clause_type = Column(String(60), nullable=True)

    # How many times each side has rejected proposals on this clause
    opponent_rejection_count = Column(Integer, default=0, nullable=False)
    user_rejection_count = Column(Integer, default=0, nullable=False)

    # References to JurisprudenceArticle.article_id values (JSON list)
    jurisprudence_article_ids = Column(JSON, nullable=True)

    # Controls render order in the negotiation arena UI
    display_order = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    session = relationship("NegotiationSession", back_populates="clauses")
    rounds = relationship(
        "NegotiationRound",
        back_populates="clause",
        cascade="all, delete-orphan",
        order_by="NegotiationRound.id",
    )

    def __repr__(self) -> str:
        return (
            f"<NegotiationClause id={self.id} "
            f"clause_key={self.clause_key!r} "
            f"state={self.state!r} "
            f"session_id={self.session_id}>"
        )


# ---------------------------------------------------------------------------
# NegotiationRound
# ---------------------------------------------------------------------------


class NegotiationRound(Base):
    """
    One proposal or response move in the negotiation of a single clause.

    actor values:
        user | opponent

    action values:
        propose | accept | reject | counter |
        trade_offer | trade_accept | trade_reject | withdraw

    trade_offer JSON schema:
        {
            "offered_clause_key": str,
            "offered_text": str,
            "requested_clause_key": str,
            "requested_text": str,
            "rationale": str
        }
    """

    __tablename__ = "negotiation_rounds"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # FK to the parent session
    session_id = Column(
        Integer,
        ForeignKey("negotiation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # FK to the clause this round belongs to
    clause_id = Column(
        Integer,
        ForeignKey("negotiation_clauses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sequential counter within this clause's negotiation
    round_number = Column(Integer, nullable=False)

    # Who is speaking this turn
    actor = Column(String(20), nullable=False)

    # What they are doing
    action = Column(String(30), nullable=False)

    # The revised clause text being proposed (null for accept/reject)
    proposed_text = Column(Text, nullable=True)

    # Natural-language explanation from the actor (required)
    response_text = Column(Text, nullable=False)

    # Cross-clause trade payload (only populated when action = trade_*)
    trade_offer = Column(JSON, nullable=True)

    # Estimated CAD value of this specific round's outcome
    dollar_value_cad = Column(Numeric(15, 2), nullable=True)

    # AI confidence score 0-1 in this response
    ai_confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    session = relationship("NegotiationSession", back_populates="rounds")
    clause = relationship("NegotiationClause", back_populates="rounds")

    def __repr__(self) -> str:
        return (
            f"<NegotiationRound id={self.id} "
            f"clause_id={self.clause_id} "
            f"round={self.round_number} "
            f"actor={self.actor!r} "
            f"action={self.action!r}>"
        )


# ---------------------------------------------------------------------------
# NegotiationConcession
# ---------------------------------------------------------------------------


class NegotiationConcession(Base):
    """
    Running ledger — one entry per concession gave or gained during negotiation.

    direction values:
        gave  — the user conceded something to the opponent
        gained — the user won something from the opponent
    """

    __tablename__ = "negotiation_concessions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    session_id = Column(
        Integer,
        ForeignKey("negotiation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    clause_id = Column(
        Integer,
        ForeignKey("negotiation_clauses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    round_id = Column(
        Integer,
        ForeignKey("negotiation_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Whether the user gave or gained this concession
    direction = Column(String(10), nullable=False)

    # Human-readable description of what was conceded or won
    description = Column(String(500), nullable=False)

    # Estimated CAD value of this concession
    estimated_value_cad = Column(Numeric(15, 2), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<NegotiationConcession id={self.id} "
            f"direction={self.direction!r} "
            f"session_id={self.session_id} "
            f"estimated_value_cad={self.estimated_value_cad}>"
        )


# ---------------------------------------------------------------------------
# JurisprudenceArticle
# ---------------------------------------------------------------------------


class JurisprudenceArticle(Base):
    """
    Canadian case law and CITT decisions indexed by clause type and jurisdiction.

    jurisdiction_codes: JSON list, e.g. ["ON", "FED"] or ["ALL"]
    clause_types: JSON list, e.g. ["liability", "indemnification"]

    court_or_tribunal examples:
        Supreme Court of Canada | Ontario Court of Appeal |
        Federal Court | CITT | Ontario Superior Court of Justice
    """

    __tablename__ = "jurisprudence_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Stable human-readable identifier, e.g. "ON-LIABILITY-TERCON-2010"
    article_id = Column(String(80), unique=True, nullable=False, index=True)

    # Jurisdiction codes this decision applies to
    jurisdiction_codes = Column(JSON, nullable=False)

    # Clause types this decision is relevant to
    clause_types = Column(JSON, nullable=False)

    # Full name of the case, e.g. "Tercon Contractors Ltd. v. British Columbia"
    case_name = Column(String(500), nullable=False)

    # Neutral citation, e.g. "2010 SCC 4" or "CITT PR-2019-037"
    citation = Column(String(255), nullable=False)

    # Issuing court or tribunal
    court_or_tribunal = Column(String(100), nullable=False)

    # Year the decision was issued
    year = Column(Integer, nullable=False)

    # Separate column retained for cases where the decision year differs from
    # the filing or publication year
    decision_year = Column(Integer, nullable=True)

    # The legal principle established — 2 to 4 sentences
    principle = Column(Text, nullable=False)

    # Longer summary suitable for a sidebar panel
    full_summary = Column(Text, nullable=True)

    # Why this decision matters specifically for procurement contracts
    relevance_to_procurement = Column(Text, nullable=True)

    # Searchable keyword tags (JSON list of strings)
    tags = Column(JSON, nullable=True)

    # Official source URL for the full decision text
    source_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<JurisprudenceArticle article_id={self.article_id!r} "
            f"case_name={self.case_name!r} "
            f"year={self.year}>"
        )
