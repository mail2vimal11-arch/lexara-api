"""API usage and billing endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
import logging

from app.database.session import get_db
from app.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/usage")
async def get_usage(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
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
