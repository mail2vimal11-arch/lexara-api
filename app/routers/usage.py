"""API usage and quota information — live counts from AuditLog."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from app.database.session import get_db
from app.models.billing import Analysis
from app.routers.billing import PLANS
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

# Overage pricing per plan (CAD per analysis beyond the plan limit)
_OVERAGE_CAD = {"free": 0.15, "starter": 0.12, "growth": 0.10, "business": 0.00}

# Legacy fallback: users created before the plan_id column got a role-based plan
_ROLE_FALLBACK_PLAN = {"admin": "business", "procurement": "starter", "legal": "growth"}


def _resolve_plan(user) -> tuple[str, dict]:
    """Resolve the user's billing plan.

    plan_id is authoritative — it is what the Stripe webhooks write on
    upgrade/downgrade (billing.py). Role is only a fallback for legacy rows
    with no/unknown plan_id.
    """
    plan_id = getattr(user, "plan_id", None)
    if plan_id in PLANS:
        return plan_id, PLANS[plan_id]
    fallback = _ROLE_FALLBACK_PLAN.get(user.role, "free")
    return fallback, PLANS[fallback]


@router.get("/usage")
async def get_usage(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return real usage and quota information for the authenticated user.

    Counts are drawn from the AuditLog for the current calendar month.
    Quota limits come from the user's billing plan (plan_id, kept in sync by
    the Stripe webhooks); role is only a fallback for legacy accounts.
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

        # Plan info: plan_id (written by Stripe webhooks) first, role fallback
        plan_id, plan_info = _resolve_plan(current_user)
        limit       = plan_info["analyses_limit"]
        overage_cad = _OVERAGE_CAD.get(plan_id, 0.15)

        if limit == -1:
            remaining = -1   # unlimited
            overage   = 0.00
        else:
            remaining = max(0, limit - analyses_this_month)
            overage_count = max(0, analyses_this_month - limit)
            overage = round(overage_count * overage_cad, 2)

        return {
            "plan": plan_id,
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
