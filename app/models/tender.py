"""Tender / contract ingestion model."""

import uuid
from sqlalchemy import Column, String, Numeric, DateTime, JSON, func
from app.database.session import Base


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)          # TED | OCP | ProZorro
    tender_id = Column(String, unique=True, index=True)
    title = Column(String)
    description = Column(String)
    buyer = Column(String)
    supplier = Column(String)
    value = Column(Numeric)
    currency = Column(String, default="USD")
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    country = Column(String)
    cpv_code = Column(String)
    source_url = Column(String)                      # audit trail
    raw_data = Column(JSON)
    ingested_at = Column(DateTime, server_default=func.now())
