"""Feature 3: Obligation Matrix — Temporal Dependency Graph models.

Five tables form the graph:
  - contract_obligations:            obligations extracted from a single contract/SOW
  - contract_anchors:                named events that deadlines attach to
  - obligation_temporal_specs:       the deadline expression (formula, not date)
  - obligation_temporal_resolutions: cached projected dates
  - holidays:                        for business-day math

A spec stores the formula ("30 business days after contract_award"), not a
resolved date. When an anchor's date changes, the resolver recomputes every
downstream projection.

Distinct from `app.models.obligation.Obligation` (portfolio-feature flat
obligations); kept separate to avoid coupling the two feature surfaces.
"""

import uuid
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Date, DateTime, Text, JSON,
    ForeignKey, UniqueConstraint, CheckConstraint, Index, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from app.database.session import Base


_JSONType = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


class ContractObligation(Base):
    __tablename__ = "contract_obligations"

    obligation_id  = Column(String, primary_key=True, default=_uuid)
    contract_id    = Column(String, nullable=False, index=True)
    section_ref    = Column(String)
    text           = Column(Text, nullable=False)
    party          = Column(String)
    modal_verb     = Column(String)
    is_conditional = Column(Boolean, default=False)
    trigger_text   = Column(Text)
    created_at     = Column(DateTime, server_default=func.now())


class ContractAnchor(Base):
    __tablename__ = "contract_anchors"

    anchor_id      = Column(String, primary_key=True, default=_uuid)
    contract_id    = Column(String, nullable=False, index=True)
    anchor_key     = Column(String, nullable=False)
    label          = Column(String, nullable=False)
    resolved_date  = Column(Date)
    source         = Column(String, nullable=False)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("contract_id", "anchor_key", name="uq_anchor_per_contract"),
    )


class ObligationTemporalSpec(Base):
    __tablename__ = "obligation_temporal_specs"

    spec_id              = Column(String, primary_key=True, default=_uuid)
    obligation_id        = Column(
        String,
        ForeignKey("contract_obligations.obligation_id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    kind                 = Column(String, nullable=False)

    absolute_date        = Column(Date)

    offset_value         = Column(Integer)
    offset_unit          = Column(String)
    direction            = Column(String)
    anchor_id            = Column(
        String,
        ForeignKey("contract_anchors.anchor_id", ondelete="SET NULL"),
    )
    anchor_obligation_id = Column(
        String,
        ForeignKey("contract_obligations.obligation_id", ondelete="SET NULL"),
    )

    recurrence_rule      = Column(String)

    raw_phrase           = Column(Text)
    confidence           = Column(Float, default=1.0)
    created_at           = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "kind <> 'relative' OR ("
            "(CASE WHEN anchor_id IS NULL THEN 0 ELSE 1 END) + "
            "(CASE WHEN anchor_obligation_id IS NULL THEN 0 ELSE 1 END) = 1)",
            name="ck_spec_one_anchor",
        ),
        CheckConstraint(
            "kind <> 'absolute' OR absolute_date IS NOT NULL",
            name="ck_spec_absolute_has_date",
        ),
        Index("idx_specs_anchor", "anchor_id"),
        Index("idx_specs_anchor_obl", "anchor_obligation_id"),
    )


class ObligationTemporalResolution(Base):
    __tablename__ = "obligation_temporal_resolutions"

    spec_id          = Column(
        String,
        ForeignKey("obligation_temporal_specs.spec_id", ondelete="CASCADE"),
        primary_key=True,
    )
    projected_date   = Column(Date)
    status           = Column(String, nullable=False)
    dependency_path  = Column(_JSONType)
    computed_at      = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_resolutions_status", "status"),
    )


class Holiday(Base):
    __tablename__ = "holidays"

    holiday_date  = Column(Date, primary_key=True)
    jurisdiction  = Column(String, primary_key=True)
    name          = Column(String, nullable=False)
