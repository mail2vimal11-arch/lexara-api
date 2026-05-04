"""
Obligation — a single duty owed by one party under one contract.

Every PortfolioContract decomposes into a list of Obligation rows. Each
obligation says: who owes what, when it is triggered, what the deadline
is, and what penalty/cap applies if it is missed.

The `user_id` column is denormalized off PortfolioContract so the future
cross-contract cascade detector can scan all of a user's obligations in
one indexed query without joining through the contracts table.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Date,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Obligation(Base):
    """
    One contractual duty.

    obligation_type values:
        payment | delivery | sla | data_handling | reporting |
        renewal | termination_notice | indemnity | other

    party values:
        us | counterparty
    """

    __tablename__ = "obligations"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))

    contract_id = Column(
        String,
        ForeignKey("portfolio_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Denormalized for fast portfolio-wide cascade scans
    user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    obligation_type = Column(String(40), nullable=False)
    party = Column(String(20), nullable=False)

    description = Column(Text, nullable=False)

    deadline_days_from_trigger = Column(Integer, nullable=True)
    trigger_event = Column(String(100), nullable=True)
    absolute_deadline = Column(Date, nullable=True)

    penalty_formula = Column(Text, nullable=True)
    penalty_amount_cad = Column(Float, nullable=True)
    liability_cap_cad = Column(Float, nullable=True)

    source_clause_text = Column(Text, nullable=True)
    source_clause_key = Column(String(100), nullable=True)

    metadata_json = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    contract = relationship("PortfolioContract", back_populates="obligations")

    def __repr__(self) -> str:
        return (
            f"<Obligation id={self.id!r} "
            f"type={self.obligation_type!r} "
            f"party={self.party!r} "
            f"contract_id={self.contract_id!r}>"
        )
