"""Audit log model — required for procurement compliance."""

import uuid
from sqlalchemy import Column, String, DateTime, JSON, func
from app.database.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True)          # nullable for system actions
    action = Column(String, nullable=False)          # CLAUSE_ANALYZED | TENDER_INGESTED | LOGIN | etc.
    timestamp = Column(DateTime, server_default=func.now())
    details = Column(JSON)                           # arbitrary context dict
    ip_address = Column(String)
    source_url = Column(String)                      # URL of data source if applicable
