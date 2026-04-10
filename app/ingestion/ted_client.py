"""
EU TED (Tenders Electronic Daily) ingestion client.
Uses the TED Open Data REST API v3.
"""

from __future__ import annotations
import logging
from typing import Optional
from datetime import datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

SEARCH_URL = f"{settings.ted_api_base}/notices/search"
HEADERS = {
    "User-Agent": "LexaraProcurementAI/1.0 (+https://lexara.tech; procurement-research)",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def _parse_date(val: Optional[str]) -> Optional[datetime]:
    """Parse ISO date string to datetime, returning None on failure."""
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_ted_data(query: str = "IT services", page: int = 1, page_size: int = 20) -> list[dict]:
    """
    Search for procurement notices on TED.
    Normalizes results into the unified tender schema.

    Args:
        query:     Free-text search term.
        page:      Page number (1-indexed).
        page_size: Results per page.

    Returns:
        List of normalized tender dicts.
    """
    payload = {
        "query": query,
        "page": page,
        "pageSize": page_size,
        "fields": ["ND", "TI", "PC", "AC", "DT", "TVH", "OJD", "CY", "AU"],
    }

    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS) as client:
        try:
            response = await client.post(SEARCH_URL, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"TED HTTP error: {e.response.status_code} — {e}")
            raise
        except Exception as e:
            logger.error(f"TED fetch error: {e}")
            raise

    notices = data.get("notices", [])
    tenders = []

    for n in notices:
        nd = n.get("ND", "")
        tenders.append({
            "source": "TED",
            "tender_id": f"ted-{nd}",
            "title": n.get("TI", ""),
            "description": n.get("TD", n.get("TI", "")),
            "buyer": n.get("AU", ""),
            "supplier": "",
            "value": float(n["TVH"]) if n.get("TVH") else None,
            "currency": "EUR",
            "start_date": _parse_date(n.get("DT")),
            "end_date": _parse_date(n.get("OJD")),
            "country": n.get("CY", ""),
            "cpv_code": ",".join(n.get("PC", [])) if isinstance(n.get("PC"), list) else n.get("PC", ""),
            "source_url": f"https://ted.europa.eu/en/notice/-/detail/{nd}",
            "raw_data": n,
        })

    logger.info(f"TED: fetched {len(tenders)} notices")
    return tenders
