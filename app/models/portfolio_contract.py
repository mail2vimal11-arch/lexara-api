"""
PortfolioContract — a single contract in a user's contract portfolio.

This is the top-level node in the Lexara "Blast Radius" engine: every
obligation, every cross-contract cascade lookup, and every counterparty
exposure roll-up hangs off a PortfolioContract row.

Each contract is owned by exactly one user (user_id) and may have many
Obligation rows attached to it via cascade delete.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Date,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database.session import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


class PortfolioContract(Base):
    """
    One contract in a user's portfolio.

    our_role values:
        buyer | seller | subcontractor | prime

    contract_type values:
        it_services | goods | construction | consulting | other

    status values:
        draft | active | expired | terminated
    """

    __tablename__ = "portfolio_contracts"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))

    user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    counterparty_name = Column(String(255), nullable=False)

    our_role = Column(String(40), nullable=False)
    contract_type = Column(String(40), nullable=False)

    contract_value_cad = Column(Float, nullable=True)
    currency = Column(String(10), nullable=False, default="CAD")

    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    status = Column(String(20), nullable=False, default="active")

    jurisdiction_code = Column(String(10), nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    obligations = relationship(
        "Obligation",
        back_populates="contract",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<PortfolioContract id={self.id!r} "
            f"name={self.name!r} "
            f"counterparty={self.counterparty_name!r} "
            f"status={self.status!r}>"
        )
