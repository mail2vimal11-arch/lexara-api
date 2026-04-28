"""Canadian jurisdiction model — covers all 14 jurisdictions (federal + 10 provinces + 3 territories)."""

from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base


class Jurisdiction(Base):
    """
    Represents a Canadian procurement jurisdiction.

    Codes:
        Federal  : FED
        Provinces: ON, BC, AB, QC, SK, MB, NB, NS, PEI, NL
        Territories: YT, NWT, NU
    """

    __tablename__ = "jurisdictions"

    # Primary key — Integer for efficient FK joins
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Short code used throughout the system (e.g. "ON", "FED", "BC")
    code = Column(String(10), unique=True, nullable=False, index=True)

    # Display names
    name = Column(String(100), nullable=False)
    name_fr = Column(String(100), nullable=True)

    # Classification: "federal" | "province" | "territory"
    jtype = Column(String(20), nullable=False)

    # Trade agreements applicable to this jurisdiction
    # e.g. ["CFTA", "CUSMA", "NWPTA", "CETA"]
    trade_agreements = Column(JSON, nullable=True)

    # Web presence
    procurement_portal_url = Column(String(500), nullable=True)

    # Governing legislation
    legislation_name = Column(String(255), nullable=True)
    legislation_url = Column(String(500), nullable=True)

    # Policy flags
    requires_bilingual = Column(Boolean, nullable=False, default=False)
    has_indigenous_set_aside = Column(Boolean, nullable=False, default=False)

    # New West Partnership Trade Agreement members: BC, AB, SK
    nwpta_member = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    frameworks = relationship(
        "ProcurementFramework",
        back_populates="jurisdiction",
        cascade="all, delete-orphan",
        lazy="select",
    )
    knowledge_articles = relationship(
        "KnowledgeArticle",
        back_populates="jurisdiction",
        lazy="select",
    )
    sow_templates = relationship(
        "SOWTemplate",
        back_populates="jurisdiction",
        lazy="select",
    )
    evaluation_templates = relationship(
        "EvaluationTemplate",
        back_populates="jurisdiction",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Jurisdiction code={self.code!r} name={self.name!r} jtype={self.jtype!r}>"
