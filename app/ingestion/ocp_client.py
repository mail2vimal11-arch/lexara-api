"""
OCP (Open Contracting Partnership) OCDS ingestion client.
Fetches procurement package listings from the OCP CKAN data registry.
"""

from __future__ import annotations
import logging
from typing import Optional
from datetime import datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = f"{settings.ocp_api_base}/package_search"
HEADERS = {
    "User-Agent": "LexaraProcurementAI/1.0 (+https://lexara.tech; procurement-research)",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_ocp_data(query: str = "tender", rows: int = 50) -> list[dict]:
    """
    Fetch procurement notices from the OCP CKAN data registry.
    Normalizes results into the unified tender schema.

    Args:
        query: Search keyword for filtering packages.
        rows:  Max number of results to return.

    Returns:
        List of normalized tender dicts.
    """
    params = {"q": query, "rows": rows}

    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS) as client:
        try:
            response = await client.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"OCP HTTP error: {e.response.status_code} — {e}")
            raise
        except Exception as e:
            logger.error(f"OCP fetch error: {e}")
            raise

    results = data.get("result", {}).get("results", [])
    tenders = []

    for item in results:
        # OCP CKAN packages don't always have structured dates — parse defensively
        tenders.append({
            "source": "OCP",
            "tender_id": f"ocp-{item.get('id', '')}",
            "title": item.get("title", ""),
            "description": item.get("notes", ""),
            "buyer": item.get("organization", {}).get("title", "") if isinstance(item.get("organization"), dict) else "",
            "supplier": "",
            "value": None,
            "currency": "USD",
            "start_date": None,
            "end_date": None,
            "country": item.get("country", ""),
            "cpv_code": "",
            "source_url": f"https://data.open-contracting.org/dataset/{item.get('name', '')}",
            "raw_data": item,
        })

    logger.info(f"OCP: fetched {len(tenders)} tenders")
    return tenders
