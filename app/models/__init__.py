"""
Lexara ORM model registry.

Importing this package is sufficient to register all models with
SQLAlchemy's declarative Base so that Base.metadata.create_all()
creates every table.
"""

from app.models.user import User
from app.models.clause import SOWClause
from app.models.tender import Tender
from app.models.audit import *  # noqa: F401,F403 — re-exports whatever audit defines
from app.models.jurisdiction import Jurisdiction
from app.models.commodity import CommoditySector, CommodityCategory, CommoditySubcategory
from app.models.knowledge import (
    ProcurementFramework,
    KnowledgeArticle,
    SOWTemplate,
    EvaluationTemplate,
    SLATemplate,
    WorkbenchSession,
)

# Feature 6: Negotiation Simulator models (guarded — module may not exist yet)
try:
    from app.models.negotiation import (
        NegotiationSession,
        NegotiationClause,
        NegotiationRound,
        NegotiationConcession,
        JurisprudenceArticle,
    )
    _negotiation_exports = [
        "NegotiationSession",
        "NegotiationClause",
        "NegotiationRound",
        "NegotiationConcession",
        "JurisprudenceArticle",
    ]
except ImportError:
    _negotiation_exports = []

__all__ = [
    "User",
    "SOWClause",
    "Tender",
    "Jurisdiction",
    "CommoditySector",
    "CommodityCategory",
    "CommoditySubcategory",
    "ProcurementFramework",
    "KnowledgeArticle",
    "SOWTemplate",
    "EvaluationTemplate",
    "SLATemplate",
    "WorkbenchSession",
    *_negotiation_exports,
]
