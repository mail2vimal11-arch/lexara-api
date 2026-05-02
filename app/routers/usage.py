"""API usage and billing endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from datetime import datetime, timedelta
import logging

from app.database.session import get_db
from app.models.billing import Analysis
from app.routers.billing import PLANS
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

    CA-005: returns real data from the DB instead of hardcoded stubs.
    - analyses_used_this_month: actual Analysis rows for this billing period
    - plan/limits: derived from the authenticated user's plan_id
    """
    try:
        plan_id   = current_user.plan_id or "free"
        plan_info = PLANS.get(plan_id, PLANS["free"])

        # Start of current calendar month (UTC)
        now         = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # First day of next month
        next_month  = (month_start + timedelta(days=32)).replace(day=1)

        analyses_used = (
            db.query(func.count(Analysis.id))
            .filter(
                Analysis.user_id == current_user.id,
                Analysis.created_at >= month_start,
            )
            .scalar()
        ) or 0

        limit     = plan_info["analyses_limit"]
        remaining = max(0, limit - analyses_used) if limit != -1 else -1  # -1 = unlimited

        return {
            "plan": plan_id,
            "analyses_used_this_month": analyses_used,
            "analyses_limit": limit,
            "remaining_quota": remaining,
            "reset_date": next_month.isoformat(),
            "overage_cost_per_analysis": 0.12,
            "estimated_overage_charges": 0.00,
            "next_billing_date": next_month.isoformat(),
        }

    except Exception as e:
        logger.error(f"Usage lookup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve usage information")
