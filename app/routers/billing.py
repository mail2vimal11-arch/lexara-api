"""Stripe billing — checkout, webhooks, portal, plan info."""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import stripe
import logging

from app.config import settings
from app.database.session import get_db
from app.models.user import User
from app.models.billing import BillingEvent
from app.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

stripe.api_key = settings.stripe_secret_key

# ── Plan config ───────────────────────────────────────────────
PLANS = {
    "free": {
        "name": "Free",
        "price_cad": 0,
        "analyses_limit": 5,
        "api_access": False,
        "price_id": None,
    },
    "starter": {
        "name": "Starter",
        "price_cad": 19,
        "analyses_limit": 50,
        "api_access": False,
        "price_id": settings.stripe_price_starter,
    },
    "growth": {
        "name": "Growth",
        "price_cad": 59,
        "analyses_limit": 500,
        "api_access": True,
        "price_id": settings.stripe_price_growth,
    },
    "business": {
        "name": "Business",
        "price_cad": 199,
        "analyses_limit": -1,  # unlimited
        "api_access": True,
        "price_id": settings.stripe_price_business,
    },
}


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/plans")
async def list_plans():
    """Return all available plans and their features."""
    return {"plans": PLANS}


class CheckoutRequest(BaseModel):
    plan_id: str
    success_url: Optional[str] = None  # defaults to settings.frontend_url
    cancel_url: Optional[str] = None


@router.post("/checkout")
async def create_checkout(
    request: CheckoutRequest,
    current_user=Depends(get_current_user),
):
    """
    Create a Stripe Checkout session for the authenticated user.

    CA-003: requires auth — unauthenticated callers cannot create Stripe sessions.
    CA-019: success_url separator is now ? or & depending on whether URL has query params.
    """
    plan = PLANS.get(request.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {request.plan_id}")
    if plan["price_id"] is None:
        raise HTTPException(status_code=400, detail="Free plan does not require checkout")

    # Use authenticated user's email — prevents email impersonation
    email = current_user.email

    # CA-019: append session_id with correct separator
    base_success = request.success_url or "https://lexara.tech?checkout=success"
    sep = "&" if "?" in base_success else "?"
    success_url = f"{base_success}{sep}session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = request.cancel_url or "https://lexara.tech?checkout=cancelled"

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=email,
            line_items=[{"price": plan["price_id"], "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"plan_id": request.plan_id, "user_id": current_user.id, "email": email},
            subscription_data={
                "metadata": {"plan_id": request.plan_id, "user_id": current_user.id}
            },
            allow_promotion_codes=True,
            billing_address_collection="auto",
            tax_id_collection={"enabled": True},
        )
        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "plan": plan["name"],
            "amount_cad": plan["price_cad"],
        }
    except stripe.StripeError as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=502, detail=f"Payment provider error: {str(e)}")


@router.post("/portal")
async def create_portal(current_user=Depends(get_current_user)):
    """
    Create a Stripe Customer Portal session for billing management.
    User can update payment method, cancel, or upgrade/downgrade plan.
    """
    # TODO: Look up stripe_customer_id from DB using current_user
    # For now return a helpful message
    raise HTTPException(
        status_code=501,
        detail="Customer portal requires account login — coming soon."
    )


@router.post("/webhooks/stripe")
@router.post("/webhook")
async def stripe_webhook(request: Request, db=Depends(get_db)):
    """
    Stripe webhook handler.
    Handles: checkout.session.completed, customer.subscription.updated,
             customer.subscription.deleted, invoice.payment_failed

    CA-004: all four handlers now perform real DB updates.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        logger.error(f"Webhook parse error: {e}")
        raise HTTPException(status_code=400, detail="Webhook parse error")

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Stripe webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, db)

    elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
        await _handle_subscription_updated(data, db)

    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_cancelled(data, db)

    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data, db)

    return JSONResponse({"received": True})


# ── Webhook handlers ──────────────────────────────────────────

async def _handle_checkout_completed(session, db):
    """Upgrade user's plan after successful Stripe Checkout. CA-004."""
    email   = session.get("customer_email") or session.get("metadata", {}).get("email")
    plan_id = session.get("metadata", {}).get("plan_id", "starter")
    cust_id = session.get("customer")

    if not email:
        logger.error("checkout.session.completed: no email in session, skipping")
        return

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning(f"checkout.session.completed: no user found for email={email}")
        return

    user.plan_id = plan_id
    if cust_id:
        user.stripe_customer_id = cust_id
    db.commit()
    logger.info(f"Upgraded user {email} to plan={plan_id} stripe_customer={cust_id}")


async def _handle_subscription_updated(subscription, db):
    """Sync plan when Stripe subscription changes. CA-004."""
    cust_id = subscription.get("customer")
    status  = subscription.get("status")
    plan_id = subscription.get("metadata", {}).get("plan_id")

    if not cust_id:
        logger.error("subscription.updated: missing customer id, skipping")
        return

    user = db.query(User).filter(User.stripe_customer_id == cust_id).first()
    if not user:
        logger.warning(f"subscription.updated: no user for customer={cust_id}")
        return

    # Only apply plan change when subscription is live
    if status in ("active", "trialing") and plan_id and plan_id in PLANS:
        user.plan_id = plan_id
        db.commit()
        logger.info(f"Updated user {user.email} plan={plan_id} status={status}")
    else:
        logger.info(f"subscription.updated: no plan change applied (status={status}, plan={plan_id})")


async def _handle_subscription_cancelled(subscription, db):
    """Downgrade user to free plan when subscription is cancelled. CA-004."""
    cust_id = subscription.get("customer")

    if not cust_id:
        logger.error("subscription.deleted: missing customer id, skipping")
        return

    user = db.query(User).filter(User.stripe_customer_id == cust_id).first()
    if not user:
        logger.warning(f"subscription.deleted: no user for customer={cust_id}")
        return

    user.plan_id = "free"
    db.commit()
    logger.info(f"Downgraded user {user.email} to free (subscription cancelled)")


async def _handle_payment_failed(invoice, db):
    """Log payment failure as a BillingEvent. CA-004.

    We log the failure but do not immediately downgrade the account —
    Stripe's built-in dunning (Smart Retries) handles retries and sends
    the subscription.deleted event if all retries fail.
    """
    cust_id = invoice.get("customer")
    amount  = invoice.get("amount_due", 0)

    logger.warning(f"Payment failed: customer={cust_id} amount_due={amount}")

    if not cust_id:
        return

    user = db.query(User).filter(User.stripe_customer_id == cust_id).first()
    if not user:
        logger.warning(f"invoice.payment_failed: no user for customer={cust_id}")
        return

    event = BillingEvent(
        user_id=user.id,
        event_type="payment_failed",
        amount_cents=amount,
        stripe_invoice_id=invoice.get("id"),
    )
    db.add(event)
    db.commit()
    logger.info(f"Logged payment_failed BillingEvent for user {user.email}")
