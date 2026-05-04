"""
Ingestion orchestrator — runs all source clients, deduplicates,
persists to DB, and triggers clause learning pipeline.
"""

from __future__ import annotations
import logging
import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.ingestion.ocp_client import fetch_ocp_data
from app.ingestion.ted_client import fetch_ted_data
from app.models.tender import Tender
from app.models.audit import AuditLog
from app.ingestion.learning import learn_from_tender
from app.nlp.search import add_clause_to_index

logger = logging.getLogger(__name__)


async def run_ingestion(db: Session, query: str = "procurement") -> dict:
    """
    Full ingestion run:
      1. Fetch from OCP + TED
      2. Deduplicate against existing DB records
      3. Persist new tenders
      4. Trigger clause learning pipeline on each new tender
      5. Write audit log entry

    Returns summary dict with counts.
    """
    results = {"ocp": 0, "ted": 0, "new": 0, "skipped": 0, "clauses_learned": 0, "errors": []}
    # Accumulate clauses to add to FAISS only after db.commit() succeeds
    _faiss_queue: list[tuple[str, str, str]] = []  # (clause_id, full_text, clause_type)

    # Fetch from all sources
    raw: list[dict] = []
    try:
        ocp_data = await fetch_ocp_data(query=query)
        raw.extend(ocp_data)
        results["ocp"] = len(ocp_data)
    except Exception as e:
        msg = f"OCP fetch failed: {e}"
        logger.error(msg)
        results["errors"].append(msg)

    try:
        ted_data = await fetch_ted_data(query=query)
        raw.extend(ted_data)
        results["ted"] = len(ted_data)
    except Exception as e:
        msg = f"TED fetch failed: {e}"
        logger.error(msg)
        results["errors"].append(msg)

    # Persist new records
    for item in raw:
        tender_id = item.get("tender_id")
        if not tender_id:
            continue

        existing = db.query(Tender).filter(Tender.tender_id == tender_id).first()
        if existing:
            results["skipped"] += 1
            continue

        # Coerce raw_data to be JSON-serializable
        raw_data = item.get("raw_data", {})
        try:
            json.dumps(raw_data)
        except (TypeError, ValueError):
            raw_data = {}

        tender = Tender(
            source=item["source"],
            tender_id=tender_id,
            title=item.get("title", ""),
            description=item.get("description", ""),
            buyer=item.get("buyer", ""),
            supplier=item.get("supplier", ""),
            value=item.get("value"),
            currency=item.get("currency", "USD"),
            start_date=item.get("start_date"),
            end_date=item.get("end_date"),
            country=item.get("country", ""),
            cpv_code=item.get("cpv_code", ""),
            source_url=item.get("source_url", ""),
            raw_data=raw_data,
        )
        db.add(tender)
        # CA-011: no per-item flush — Tender.id is a Python-generated UUID so
        # the PK is already set on the object.  A single db.commit() below
        # persists everything in one round-trip.

        # Learn clauses from this tender's description.
        # learn_from_tender adds clause rows to the DB session but does NOT
        # update FAISS — that happens below after db.commit() to keep them in sync.
        if tender.description:
            learned = learn_from_tender(db, tender)
            results["clauses_learned"] += len(learned)
            _faiss_queue.extend(
                (c["clause_id"], c["full_text"], c["clause_type"])
                for c in learned
            )

        results["new"] += 1

    db.commit()

    # Add to FAISS only after a successful commit so DB and index stay in sync
    for clause_id, full_text, clause_type in _faiss_queue:
        try:
            add_clause_to_index(clause_id, full_text, clause_type)
        except Exception as e:
            logger.warning(f"FAISS index failed for clause {clause_id}: {e}")

    # Audit log
    audit = AuditLog(
        action="TENDER_INGESTION_RUN",
        details={
            "ocp_fetched": results["ocp"],
            "ted_fetched": results["ted"],
            "new_saved": results["new"],
            "skipped": results["skipped"],
            "clauses_learned": results["clauses_learned"],
            "errors": results["errors"],
        },
    )
    db.add(audit)
    db.commit()

    logger.info(f"Ingestion complete: {results}")
    return results
