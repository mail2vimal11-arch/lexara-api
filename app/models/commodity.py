"""
Commodity / industry sector taxonomy for Canadian government procurement.

Three-level hierarchy:
    CommoditySector  (e.g. "IT_DIGITAL")
    └─ CommodityCategory  (e.g. "IT_CLOUD")
       └─ CommoditySubcategory  (e.g. "IT_CLOUD_IAAS")
"""

from sqlalchemy import Column, Integer, String, Text, JSON, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database.session import Base


class CommoditySector(Base):
    """
    Top-level industry grouping.

    Example codes:
        IT_DIGITAL, PROF_SVC, CONSTRUCTION, HEALTH_LIFE, GOODS_SUPPLY,
        ENERGY_ENV, SECURITY_DEFENCE, TRANSPORT_LOGISTICS, AGRICULTURE,
        FINANCIAL_INS, EDUCATION_RESEARCH, INDIGENOUS_COMMUNITY,
        LEGAL_REGULATORY, FACILITIES_MGMT
    """

    __tablename__ = "commodity_sectors"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Stable machine-readable code
    code = Column(String(30), unique=True, nullable=False, index=True)

    # Display names (bilingual)
    name = Column(String(100), nullable=False)
    name_fr = Column(String(100), nullable=True)

    description = Column(Text, nullable=True)

    # Emoji used by the Lexara UI sidebar
    ui_icon = Column(String(50), nullable=True)

    # Controls ordering in UI picker
    display_order = Column(Integer, nullable=False, default=0)

    # Relationships
    categories = relationship(
        "CommodityCategory",
        back_populates="sector",
        cascade="all, delete-orphan",
        order_by="CommodityCategory.display_order",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<CommoditySector code={self.code!r} name={self.name!r}>"


class CommodityCategory(Base):
    """
    Mid-level commodity grouping within a sector.

    Example codes:
        IT_CLOUD, IT_SOFTWARE_LIC, IT_CYBER, IT_APP_DEV
    """

    __tablename__ = "commodity_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # FK to parent sector
    sector_id = Column(
        Integer, ForeignKey("commodity_sectors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Stable machine-readable code
    code = Column(String(50), unique=True, nullable=False, index=True)

    # Display names (bilingual)
    name = Column(String(100), nullable=False)
    name_fr = Column(String(100), nullable=True)

    description = Column(Text, nullable=True)

    # Procurement method types typically used in this category
    # e.g. ["RFP", "RFSO", "ITT"]
    typical_contract_types = Column(JSON, nullable=True)

    # Typical contract duration
    typical_duration_months = Column(Integer, nullable=True)

    # Indicative value ranges in CAD
    value_range_min_cad = Column(Numeric(15, 2), nullable=True)
    value_range_max_cad = Column(Numeric(15, 2), nullable=True)

    # Cross-walk to international coding standards
    cpv_codes = Column(JSON, nullable=True)    # EU Common Procurement Vocabulary
    unspsc_codes = Column(JSON, nullable=True)  # UN/SPSC

    # Procurement-officer advisory notes specific to this category
    # e.g. ["Check for mandatory security screening", "Confirm data residency requirements"]
    key_considerations = Column(JSON, nullable=True)

    display_order = Column(Integer, nullable=False, default=0)

    # Relationships
    sector = relationship("CommoditySector", back_populates="categories")
    subcategories = relationship(
        "CommoditySubcategory",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="CommoditySubcategory.id",
        lazy="select",
    )
    knowledge_articles = relationship(
        "KnowledgeArticle",
        back_populates="commodity_category",
        lazy="select",
    )
    sow_templates = relationship(
        "SOWTemplate",
        back_populates="commodity_category",
        lazy="select",
    )
    evaluation_templates = relationship(
        "EvaluationTemplate",
        back_populates="commodity_category",
        lazy="select",
    )
    sla_templates = relationship(
        "SLATemplate",
        back_populates="commodity_category",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<CommodityCategory code={self.code!r} name={self.name!r}>"


class CommoditySubcategory(Base):
    """
    Fine-grained procurement type within a category.

    Carries special-requirement flags and standard deliverable/criteria lists
    used to pre-populate the Lexara Workbench.
    """

    __tablename__ = "commodity_subcategories"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # FK to parent category
    category_id = Column(
        Integer,
        ForeignKey("commodity_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Stable machine-readable code
    code = Column(String(60), unique=True, nullable=False, index=True)

    # Display names (bilingual)
    name = Column(String(100), nullable=False)
    name_fr = Column(String(100), nullable=True)

    description = Column(Text, nullable=True)

    # Applicable compliance / policy flags
    # e.g. ["SECURITY_CLEARANCE_REQUIRED", "CANADIAN_DATA_RESIDENCY",
    #        "BILINGUAL_REQUIRED", "LICENSED_PROFESSION"]
    special_requirements = Column(JSON, nullable=True)

    # Canonical deliverable types for SOW generation
    # e.g. ["Project Plan", "Status Reports", "Source Code", "Training Materials"]
    typical_deliverables = Column(JSON, nullable=True)

    # Standard evaluation criteria names for evaluation plan generation
    # e.g. ["Technical Approach", "Team Qualifications", "Management Plan", "Price"]
    typical_evaluation_criteria = Column(JSON, nullable=True)

    # Relationships
    category = relationship("CommodityCategory", back_populates="subcategories")
    knowledge_articles = relationship(
        "KnowledgeArticle",
        back_populates="commodity_subcategory",
        lazy="select",
    )
    sow_templates = relationship(
        "SOWTemplate",
        back_populates="commodity_subcategory",
        lazy="select",
    )
    sla_templates = relationship(
        "SLATemplate",
        back_populates="commodity_subcategory",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<CommoditySubcategory code={self.code!r} name={self.name!r}>"
