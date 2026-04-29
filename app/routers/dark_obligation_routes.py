"""
Dark Obligation Detector endpoints — /v1/dark-obligations/

Routes:
    POST   /v1/dark-obligations/detect              Run dark-obligation detection on a SOW
    GET    /v1/dark-obligations/catalog             Return the full standard-clause catalog
    GET    /v1/dark-obligations/catalog/{type}      Return the catalog for one contract type

A "dark obligation" is a clause that peers commonly include in contracts of a
given type but that is *missing* from the SOW under review.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security import get_current_user
from app.services.dark_obligation_service import (
    STANDARD_CLAUSE_CATALOG,
    cuad_frequencies_meta,
    detect_dark_obligations,
    detect_dark_obligations_general,
    get_catalog_for,
    list_cuad_categories,
    list_supported_contract_types,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/dark-obligations", tags=["dark-obligations"])


# ── Request models ──────────────────────────────────────────────────────────


class DetectRequest(BaseModel):
    sow_text: str = Field(..., description="Full SOW / contract text to analyse")
    contract_type: str = Field(
        ...,
        description="Contract type key (one of the catalog keys, e.g. 'it_services')",
    )
    presence_threshold: Optional[float] = Field(
        0.55,
        ge=0.0,
        le=1.0,
        description="Cosine similarity above which a probe is treated as present",
    )
    min_peer_frequency: Optional[float] = Field(
        0.50,
        ge=0.0,
        le=1.0,
        description="Only flag missing clauses with peer frequency at or above this",
    )


# ── Routes ──────────────────────────────────────────────────────────────────


@router.post("/detect")
def detect(
    request: DetectRequest,
    current_user=Depends(get_current_user),
):
    """
    Run dark-obligation detection on a SOW.

    Returns the list of missing standard clauses, the list of clauses found
    present, and a one-line human summary.
    """
    if not request.sow_text or len(request.sow_text) <= 100:
        raise HTTPException(
            status_code=400,
            detail="sow_text must be longer than 100 characters",
        )
    if request.contract_type not in STANDARD_CLAUSE_CATALOG:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported contract_type '{request.contract_type}'. "
                f"Supported: {', '.join(list_supported_contract_types())}."
            ),
        )

    try:
        result = detect_dark_obligations(
            sow_text=request.sow_text,
            contract_type=request.contract_type,
            presence_threshold=request.presence_threshold or 0.55,
            min_peer_frequency=request.min_peer_frequency or 0.50,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dark-obligation detection failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to run dark-obligation detection",
        )


@router.get("/catalog")
def get_full_catalog(current_user=Depends(get_current_user)):
    """
    Return the full standard-clause catalog so the frontend can show users
    what we look for, broken down by contract type.
    """
    return {
        "contract_types": list_supported_contract_types(),
        "catalog": STANDARD_CLAUSE_CATALOG,
    }


class DetectGeneralRequest(BaseModel):
    sow_text: str = Field(..., description="Full SOW / contract text to analyse")
    presence_threshold: Optional[float] = Field(
        0.55,
        ge=0.0,
        le=1.0,
        description="Cosine similarity above which a probe is treated as present",
    )
    min_peer_frequency: Optional[float] = Field(
        0.30,
        ge=0.0,
        le=1.0,
        description=(
            "Only flag missing CUAD categories with peer frequency at or above this"
        ),
    )


@router.post("/detect-general")
def detect_general(
    request: DetectGeneralRequest,
    current_user=Depends(get_current_user),
):
    """
    Run dark-obligation detection against the CUAD-derived *general* catalog
    of 41 commercial-contract clause categories.

    Uses peer frequencies measured from the public CUAD corpus
    (n=510 contracts) rather than hand-curated estimates. Complements
    `/detect`, which scans a contract-type-specific catalog.
    """
    if not request.sow_text or len(request.sow_text) <= 100:
        raise HTTPException(
            status_code=400,
            detail="sow_text must be longer than 100 characters",
        )
    try:
        result = detect_dark_obligations_general(
            sow_text=request.sow_text,
            presence_threshold=request.presence_threshold or 0.55,
            min_peer_frequency=request.min_peer_frequency or 0.30,
        )
        if result.get("error") == "cuad_not_available":
            raise HTTPException(status_code=503, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"CUAD-based dark-obligation detection failed: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to run CUAD dark-obligation detection",
        )


@router.get("/cuad-catalog")
def get_cuad_catalog(current_user=Depends(get_current_user)):
    """
    Return the CUAD-derived general clause catalog with measured peer
    frequencies and the dataset metadata block.
    """
    catalog = list_cuad_categories()
    meta = cuad_frequencies_meta()
    if not catalog:
        raise HTTPException(
            status_code=503,
            detail=(
                "CUAD frequencies have not been ingested. "
                "Run `python scripts/ingest_cuad.py` to generate "
                "`app/services/cuad_frequencies.json`."
            ),
        )
    return {
        "_meta": meta,
        "categories": catalog,
        "count": len(catalog),
    }


@router.get("/catalog/{contract_type}")
def get_catalog_by_type(
    contract_type: str,
    current_user=Depends(get_current_user),
):
    """Return the catalog for a single contract type."""
    catalog = get_catalog_for(contract_type)
    if catalog is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown contract_type '{contract_type}'. "
                f"Supported: {', '.join(list_supported_contract_types())}."
            ),
        )
    return {
        "contract_type": contract_type,
        "clauses": catalog,
    }
