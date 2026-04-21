"""Audit logging service — call this for every significant action."""

from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def log_action(
    db: Session,
    action: str,
    details: dict | None = None,
    user_id: str | None = None,
    ip_address: str | None = None,
    source_url: str | None = None,
) -> None:
    """
    Write an audit log entry.

    Args:
        db:         Database session.
        action:     Action name (e.g., 'CLAUSE_ANALYZED', 'LOGIN', 'TENDER_INGESTED').
        details:    Arbitrary context dict (will be stored as JSONB).
        user_id:    ID of the acting user (None for system actions).
        ip_address: Request IP address.
        source_url: URL of data source, if applicable.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        details=details or {},
        ip_address=ip_address,
        source_url=source_url,
    )
    db.add(entry)
    db.commit()
