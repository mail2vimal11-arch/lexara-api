"""API usage and billing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header
from datetime import datetime, timedelta
import logging

from app.database.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/usage")
async def get_usage(
    authorization: str = Header(None),
    db = Depends(get_db)
):
    """
    Get API usage and quota information.
    
    Returns:
    - Current plan
    - Analyses used this month
    - Remaining quota
    - Reset date
    - Overage charges
    """
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    try:
        # TODO: Implement usage lookup from database
        return {
            "plan": "growth",
            "analyses_used_this_month": 150,
            "analyses_limit": 500,
            "remaining_quota": 350,
            "reset_date": (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1).isoformat(),
            "overage_cost_per_analysis": 0.12,
            "estimated_overage_charges": 0.00,
            "next_billing_date": (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Usage lookup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve usage information")
