"""SOW clause library model."""

import uuid
from sqlalchemy import Column, String, Float, DateTime, func, Boolean
from app.database.session import Base


class SOWClause(Base):
    __tablename__ = "sow_clauses"

    clause_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tender_id = Column(String, nullable=True)        # nullable for hand-authored clauses
    source = Column(String)                          # TED | OCP | Custom | Ontario
    clause_text = Column(String, nullable=False)
    clause_type = Column(String)                     # Deliverables | Services | Timeline | etc.
    subtype = Column(String)
    jurisdiction = Column(String, default="CA-ON")
    industry = Column(String)
    risk_level = Column(String, default="Low")       # Low | Medium | High
    confidence_score = Column(Float, default=1.0)
    is_standard = Column(Boolean, default=False)     # True = hand-curated canonical clause
    created_at = Column(DateTime, server_default=func.now())
