"""Ingestion trigger and tender listing routes."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.ingestion.pipeline import run_ingestion
from app.models.tender import Tender
from app.models.user import User
from app.security import require_role

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


class IngestRequest(BaseModel):
    query: str = "procurement"


@router.post("/run")
async def trigger_ingestion(
    req: IngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    Trigger a full ingestion run (admin only).
    Fetches from OCP + TED, persists new tenders, learns clauses.
    """
    result = await run_ingestion(db, query=req.query)
    return result


@router.get("/tenders")
async def list_tenders(
    source: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("procurement")),
):
    """List ingested tenders with optional source/country filters.
    Seeds reference tenders and attempts live ingestion if table is empty."""
    if db.query(Tender).count() == 0:
        # Seed reference tenders instantly — no external API calls
        from app.services.tender_seed import seed_tenders
        seed_tenders(db)

    q = db.query(Tender)
    if source:
        q = q.filter(Tender.source == source.upper())
    if country:
        q = q.filter(Tender.country == country)
    total = q.count()
    tenders = q.order_by(Tender.ingested_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "tenders": [
            {
                "id": t.id,
                "source": t.source,
                "tender_id": t.tender_id,
                "title": t.title,
                "buyer": t.buyer,
                "value": float(t.value) if t.value else None,
                "currency": t.currency,
                "country": t.country,
                "source_url": t.source_url,
                "ingested_at": t.ingested_at.isoformat() if t.ingested_at else None,
            }
            for t in tenders
        ],
    }
