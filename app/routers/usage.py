"""API usage and quota information — live counts from AuditLog."""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from app.database.session import get_db
from app.security import get_current_user
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter()

# Analysis-triggering actions logged by the contracts router
ANALYSIS_ACTIONS = {
    "CONTRACT_SUMMARY",
    "CONTRACT_RISK_SCORE",
    "CONTRACT_KEY_RISKS",
    "CONTRACT_MISSING_CLAUSES",
    "CONTRACT_EXTRACT_CLAUSES",
}

# Per-role quota defaults (mirrors billing plans without requiring a plan_id column)
_ROLE_PLAN = {
    "admin":       {"plan": "business",    "analyses_limit": -1,   "overage_cad": 0.00},
    "procurement": {"plan": "starter",     "analyses_limit": 50,   "overage_cad": 0.12},
    "legal":       {"plan": "growth",      "analyses_limit": 500,  "overage_cad": 0.10},
}
_DEFAULT_PLAN = {"plan": "free", "analyses_limit": 5, "overage_cad": 0.15}


@router.get("/usage")
async def get_usage(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return real usage and quota information for the authenticated user.

    Counts are drawn from the AuditLog for the current calendar month.
    Quota limits are derived from the user's role.
    """
    try:
        # Calendar-month window
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (month_start + timedelta(days=32)).replace(day=1)

        # Count analysis actions this month for this user
        analyses_this_month: int = (
            db.query(AuditLog)
            .filter(
                AuditLog.user_id == str(current_user.id),
                AuditLog.action.in_(ANALYSIS_ACTIONS),
                AuditLog.timestamp >= month_start,
                AuditLog.timestamp < next_month,
            )
            .count()
        )

        # Plan info from role
        plan_info = _ROLE_PLAN.get(current_user.role, _DEFAULT_PLAN)
        limit       = plan_info["analyses_limit"]
        overage_cad = plan_info["overage_cad"]

        if limit == -1:
            remaining = -1   # unlimited
            overage   = 0.00
        else:
            remaining = max(0, limit - analyses_this_month)
            overage_count = max(0, analyses_this_month - limit)
            overage = round(overage_count * overage_cad, 2)

        return {
            "plan": plan_info["plan"],
            "role": current_user.role,
            "analyses_used_this_month": analyses_this_month,
            "analyses_limit": limit,          # -1 = unlimited
            "remaining_quota": remaining,     # -1 = unlimited
            "overage_cost_per_analysis": overage_cad,
            "estimated_overage_charges": overage,
            "billing_period_start": month_start.isoformat(),
            "billing_period_end": next_month.isoformat(),
            "reset_date": next_month.isoformat(),
        }

    except Exception as e:
        logger.error(f"Usage lookup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve usage information")
