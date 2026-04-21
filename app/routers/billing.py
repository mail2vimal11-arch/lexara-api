"""Stripe billing — checkout, webhooks, portal, plan info."""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import stripe
import logging
import json

from app.config import settings
from app.database.session import get_db
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
    email: EmailStr
    success_url: Optional[str] = "https://lexara.tech?checkout=success"
    cancel_url: Optional[str] = "https://lexara.tech?checkout=cancelled"


@router.post("/checkout")
async def create_checkout(request: CheckoutRequest):
    """
    Create a Stripe Checkout session for a given plan.
    Returns a checkout URL to redirect the user to.
    """
    plan = PLANS.get(request.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {request.plan_id}")
    if plan["price_id"] is None:
        raise HTTPException(status_code=400, detail="Free plan does not require checkout")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=request.email,
            line_items=[{"price": plan["price_id"], "quantity": 1}],
            success_url=request.success_url + "&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.cancel_url,
            metadata={"plan_id": request.plan_id, "email": request.email},
            subscription_data={
                "metadata": {"plan_id": request.plan_id, "email": request.email}
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
    except stripe.error.StripeError as e:
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
async def stripe_webhook(request: Request):
    """
    Stripe webhook handler.
    Handles: checkout.session.completed, customer.subscription.updated,
             customer.subscription.deleted, invoice.payment_failed
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        logger.error(f"Webhook parse error: {e}")
        raise HTTPException(status_code=400, detail="Webhook parse error")

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Stripe webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data)

    elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
        await _handle_subscription_updated(data)

    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_cancelled(data)

    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data)

    return JSONResponse({"received": True})


# ── Webhook handlers ──────────────────────────────────────────

async def _handle_checkout_completed(session):
    email    = session.get("customer_email") or session.get("metadata", {}).get("email")
    plan_id  = session.get("metadata", {}).get("plan_id", "starter")
    cust_id  = session.get("customer")

    logger.info(f"Checkout completed: email={email} plan={plan_id} customer={cust_id}")
    # TODO: upsert User in DB — set plan_id and stripe_customer_id
    # For now just log; DB integration goes here once auth is built


async def _handle_subscription_updated(subscription):
    cust_id   = subscription.get("customer")
    status    = subscription.get("status")
    plan_id   = subscription.get("metadata", {}).get("plan_id", "starter")

    logger.info(f"Subscription updated: customer={cust_id} plan={plan_id} status={status}")
    # TODO: update User.plan_id in DB


async def _handle_subscription_cancelled(subscription):
    cust_id = subscription.get("customer")
    logger.info(f"Subscription cancelled: customer={cust_id} — downgrading to free")
    # TODO: set User.plan_id = "free" in DB


async def _handle_payment_failed(invoice):
    cust_id = invoice.get("customer")
    amount  = invoice.get("amount_due", 0)
    logger.warning(f"Payment failed: customer={cust_id} amount={amount}")
    # TODO: send dunning email, flag account
