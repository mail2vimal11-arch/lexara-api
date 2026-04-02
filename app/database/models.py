"""SQLAlchemy ORM models."""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, UUID, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database.session import Base


class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    organization_name = Column(String(255), nullable=True)
    plan_id = Column(String(50), default="free")  # free, starter, growth, business
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")
    billing_events = relationship("BillingEvent", back_populates="user", cascade="all, delete-orphan")


class APIKey(Base):
    """API keys for user authentication."""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=60)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")


class Analysis(Base):
    """Contract analysis results."""
    __tablename__ = "analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    contract_hash = Column(String(255), nullable=False, index=True)
    contract_type = Column(String(50), nullable=True)
    jurisdiction = Column(String(10), default="ON")
    analysis_data = Column(Text, nullable=False)  # JSON
    risk_score = Column(Integer, nullable=True)
    tokens_used = Column(Integer, default=0)
    backend = Column(String(50), default="claude")  # "claude" or "receiptsapi"
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow().replace(day=1) + timedelta(days=90))
    is_cached = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="analyses")


class UsageLog(Base):
    """API usage tracking for billing."""
    __tablename__ = "usage_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)
    endpoint = Column(String(255), nullable=False)
    tokens_consumed = Column(Integer, default=0)
    processing_time_ms = Column(Integer, nullable=True)
    response_status = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="usage_logs")


class BillingEvent(Base):
    """Billing events for Stripe integration."""
    __tablename__ = "billing_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # "usage_charge", "refund", "subscription"
    amount_cents = Column(Integer, nullable=False)
    tokens_consumed = Column(Integer, default=0)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    stripe_invoice_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="billing_events")
