"""
Requirement 1 — Stripe & Billing Integrity
===========================================
Tests checkout flows, webhook event processing, and billing edge cases.

Mocking strategy
----------------
- stripe.checkout.Session.create  → patched with unittest.mock.patch
- stripe.Webhook.construct_event  → patched to return controlled event payloads
- stripe.error.StripeError        → raised by mock to simulate card failures
- stripe.error.SignatureVerificationError → raised to simulate bad webhooks
No real Stripe network calls are made; no costs incurred in CI.
"""

import json
import hmac
import hashlib
import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from tests.conftest import SAMPLE_CONTRACT


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_stripe_session(plan_id: str = "starter", url: str = "https://checkout.stripe.com/pay/cs_test_abc123"):
    """Return a minimal mock Stripe Session object."""
    session = MagicMock()
    session.url = url
    session.id = "cs_test_abc123"
    session.payment_status = "unpaid"
    return session


def _build_webhook_payload(event_type: str, data: dict) -> bytes:
    """Build a raw Stripe webhook event payload."""
    event = {
        "id": "evt_test_001",
        "type": event_type,
        "data": {"object": data},
        "livemode": False,
        "api_version": "2023-10-16",
    }
    return json.dumps(event).encode()


def _sign_webhook(payload: bytes, secret: str = "whsec_test_fake_for_e2e") -> str:
    """Generate a valid Stripe-Signature header value."""
    ts = int(time.time())
    signed = f"{ts}.{payload.decode()}"
    sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


# ── B-01 to B-08: Checkout Flows ──────────────────────────────────────────────

class TestCheckoutFlows:
    """POST /v1/checkout — happy paths and schema validation."""

    @patch("stripe.checkout.Session.create")
    def test_starter_plan_checkout_returns_200(self, mock_create, client):
        """B-01: Starter plan checkout creates a session and returns checkout_url."""
        mock_create.return_value = _make_stripe_session("starter")
        resp = client.post("/v1/checkout", json={
            "plan_id": "starter",
            "email": "buyer@example.com",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "checkout_url" in body
        assert "session_id" in body
        assert body["plan"] == "Starter"
        assert body["amount_cad"] == 19

    @patch("stripe.checkout.Session.create")
    def test_growth_plan_checkout(self, mock_create, client):
        """B-02: Growth plan returns correct plan name and amount."""
        mock_create.return_value = _make_stripe_session("growth")
        resp = client.post("/v1/checkout", json={
            "plan_id": "growth",
            "email": "buyer@example.com",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["plan"] == "Growth"
        assert body["amount_cad"] == 59

    @patch("stripe.checkout.Session.create")
    def test_business_plan_checkout(self, mock_create, client):
        """B-03: Business plan returns correct plan name and amount."""
        mock_create.return_value = _make_stripe_session("business")
        resp = client.post("/v1/checkout", json={
            "plan_id": "business",
            "email": "buyer@example.com",
        })
        assert resp.status_code == 200
        assert resp.json()["plan"] == "Business"
        assert resp.json()["amount_cad"] == 199

    def test_free_plan_checkout_rejected(self, client):
        """B-04: Free plan checkout is rejected — no payment required."""
        resp = client.post("/v1/checkout", json={
            "plan_id": "free",
            "email": "buyer@example.com",
        })
        assert resp.status_code == 400
        assert "free plan" in resp.json()["detail"].lower()

    def test_unknown_plan_rejected(self, client):
        """B-05: Unknown plan returns 400."""
        resp = client.post("/v1/checkout", json={
            "plan_id": "enterprise_plus_ultra",
            "email": "buyer@example.com",
        })
        assert resp.status_code == 400
        assert "unknown plan" in resp.json()["detail"].lower()

    def test_invalid_email_rejected(self, client):
        """B-06: Pydantic EmailStr rejects malformed email with 422."""
        resp = client.post("/v1/checkout", json={
            "plan_id": "starter",
            "email": "not-an-email",
        })
        assert resp.status_code == 422

    @patch("stripe.checkout.Session.create")
    def test_stripe_error_returns_502(self, mock_create, client):
        """B-07: Stripe API failure bubbles up as 502, not 500."""
        mock_create.side_effect = __import__(
            "stripe", fromlist=["error"]
        ).error.StripeError("Card network unavailable")
        resp = client.post("/v1/checkout", json={
            "plan_id": "starter",
            "email": "buyer@example.com",
        })
        assert resp.status_code == 502
        assert "payment provider error" in resp.json()["detail"].lower()

    @patch("stripe.checkout.Session.create")
    def test_response_schema_complete(self, mock_create, client):
        """B-08: Response contains all required fields."""
        mock_create.return_value = _make_stripe_session()
        resp = client.post("/v1/checkout", json={
            "plan_id": "starter",
            "email": "schema@test.com",
        })
        assert resp.status_code == 200
        body = resp.json()
        for field in ("checkout_url", "session_id", "plan", "amount_cad"):
            assert field in body, f"Missing field: {field}"
        assert body["checkout_url"].startswith("https://")


# ── B-09 to B-15: Webhook Processing ─────────────────────────────────────────

class TestStripeWebhooks:
    """POST /v1/webhooks/stripe — event processing and signature verification."""

    WEBHOOK_ENDPOINT = "/v1/webhooks/stripe"

    def _post_event(self, client, event_type: str, data: dict,
                    secret: str = "whsec_test_fake_for_e2e",
                    tamper: bool = False):
        payload = _build_webhook_payload(event_type, data)
        sig = _sign_webhook(payload, secret)
        if tamper:
            sig = sig.replace("v1=", "v1=TAMPERED")

        mock_event = {
            "type": event_type,
            "data": {"object": data},
        }

        with patch("stripe.Webhook.construct_event", return_value=mock_event):
            return client.post(
                self.WEBHOOK_ENDPOINT,
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "stripe-signature": sig,
                },
            )

    def test_checkout_session_completed(self, client):
        """B-09: checkout.session.completed is acknowledged with 200."""
        resp = self._post_event(client, "checkout.session.completed", {
            "customer_email": "user@example.com",
            "customer": "cus_test_001",
            "metadata": {"plan_id": "starter", "email": "user@example.com"},
        })
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

    def test_subscription_deleted(self, client):
        """B-10: customer.subscription.deleted triggers downgrade handler."""
        resp = self._post_event(client, "customer.subscription.deleted", {
            "customer": "cus_test_001",
            "status": "canceled",
            "metadata": {"plan_id": "starter"},
        })
        assert resp.status_code == 200

    def test_subscription_updated(self, client):
        """B-11: customer.subscription.updated is processed."""
        resp = self._post_event(client, "customer.subscription.updated", {
            "customer": "cus_test_001",
            "status": "active",
            "metadata": {"plan_id": "growth"},
        })
        assert resp.status_code == 200

    def test_invoice_payment_failed(self, client):
        """B-12: invoice.payment_failed is handled without crashing."""
        resp = self._post_event(client, "invoice.payment_failed", {
            "customer": "cus_test_001",
            "amount_due": 1900,
        })
        assert resp.status_code == 200

    def test_invalid_signature_rejected(self, client):
        """B-13: Webhook with bad signature returns 400."""
        payload = _build_webhook_payload("checkout.session.completed", {})

        with patch(
            "stripe.Webhook.construct_event",
            side_effect=__import__("stripe", fromlist=["error"]).error.SignatureVerificationError(
                "No signatures found matching the expected signature", sig_header=""
            ),
        ):
            resp = client.post(
                self.WEBHOOK_ENDPOINT,
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "stripe-signature": "t=0,v1=invalidsignature",
                },
            )
        assert resp.status_code == 400
        assert "signature" in resp.json()["detail"].lower()

    def test_missing_signature_header_rejected(self, client):
        """B-13b: Webhook with no stripe-signature header is rejected."""
        payload = _build_webhook_payload("checkout.session.completed", {})

        with patch(
            "stripe.Webhook.construct_event",
            side_effect=__import__("stripe", fromlist=["error"]).error.SignatureVerificationError(
                "No signature header", sig_header=""
            ),
        ):
            resp = client.post(
                self.WEBHOOK_ENDPOINT,
                content=payload,
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 400

    def test_unknown_event_type_gracefully_ignored(self, client):
        """B-14: Unknown event type is received and returned 200 without crashing."""
        resp = self._post_event(client, "payment_method.attached", {
            "id": "pm_test_001",
            "type": "card",
        })
        assert resp.status_code == 200

    def test_webhook_alias_route(self, client):
        """B-15: /v1/webhook (alias) behaves identically to /v1/webhooks/stripe."""
        payload = _build_webhook_payload("checkout.session.completed", {
            "customer_email": "alias@test.com",
            "metadata": {},
        })
        mock_event = {
            "type": "checkout.session.completed",
            "data": {"object": {"customer_email": "alias@test.com", "metadata": {}}},
        }
        with patch("stripe.Webhook.construct_event", return_value=mock_event):
            resp = client.post(
                "/v1/webhook",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "stripe-signature": _sign_webhook(payload),
                },
            )
        assert resp.status_code == 200


# ── B-16 to B-19: Edge Cases ──────────────────────────────────────────────────

class TestBillingEdgeCases:
    """Card declines, 3D Secure, proration, and cancellation paths."""

    @patch("stripe.checkout.Session.create")
    def test_card_declined_returns_502(self, mock_create, client):
        """B-16: card_declined StripeError surfaces as 502."""
        err = __import__("stripe", fromlist=["error"]).error.CardError(
            "Your card was declined.",
            param="card",
            code="card_declined",
        )
        mock_create.side_effect = err
        resp = client.post("/v1/checkout", json={
            "plan_id": "starter",
            "email": "declined@test.com",
        })
        assert resp.status_code == 502
        assert "payment provider error" in resp.json()["detail"].lower()

    @patch("stripe.checkout.Session.create")
    def test_insufficient_funds_returns_502(self, mock_create, client):
        """B-17: insufficient_funds StripeError surfaces as 502."""
        err = __import__("stripe", fromlist=["error"]).error.CardError(
            "Your card has insufficient funds.",
            param="card",
            code="insufficient_funds",
        )
        mock_create.side_effect = err
        resp = client.post("/v1/checkout", json={
            "plan_id": "growth",
            "email": "nofunds@test.com",
        })
        assert resp.status_code == 502

    @patch("stripe.checkout.Session.create")
    def test_3ds_checkout_session_created_without_crash(self, mock_create, client):
        """B-18: 3DS requires_action — checkout session still created successfully.
        Stripe handles 3DS redirect in the Checkout UI; backend just creates session."""
        session = _make_stripe_session()
        session.payment_status = "requires_action"
        mock_create.return_value = session
        resp = client.post("/v1/checkout", json={
            "plan_id": "starter",
            "email": "threeds@test.com",
        })
        # Session created successfully — 3DS redirect handled client-side by Stripe
        assert resp.status_code == 200
        assert "checkout_url" in resp.json()

    @patch("stripe.checkout.Session.create")
    def test_promotion_codes_enabled_in_session_create(self, mock_create, client):
        """B-19: Verify allow_promotion_codes=True is passed to Stripe."""
        mock_create.return_value = _make_stripe_session()
        client.post("/v1/checkout", json={
            "plan_id": "starter",
            "email": "promo@test.com",
        })
        _, kwargs = mock_create.call_args
        assert kwargs.get("allow_promotion_codes") is True, (
            "allow_promotion_codes must be True to support discount codes"
        )

    def test_plans_endpoint_lists_all_tiers(self, client):
        """Smoke: GET /v1/plans returns all four tiers."""
        resp = client.get("/v1/plans")
        assert resp.status_code == 200
        plans = resp.json()["plans"]
        assert set(plans.keys()) >= {"free", "starter", "growth", "business"}

    @patch("stripe.checkout.Session.create")
    def test_subscription_data_metadata_includes_plan_id(self, mock_create, client):
        """Proration/upgrade support: subscription_data.metadata must carry plan_id."""
        mock_create.return_value = _make_stripe_session()
        client.post("/v1/checkout", json={
            "plan_id": "growth",
            "email": "upgrade@test.com",
        })
        _, kwargs = mock_create.call_args
        sub_meta = kwargs.get("subscription_data", {}).get("metadata", {})
        assert sub_meta.get("plan_id") == "growth", (
            "plan_id missing from subscription_data.metadata — "
            "webhook handler cannot determine plan on subscription.updated"
        )

    def test_webhook_subscription_deleted_event_structure(self, client):
        """Cancellation (end-of-period): deleted event carries correct fields."""
        payload = _build_webhook_payload("customer.subscription.deleted", {
            "customer": "cus_cancel_001",
            "cancel_at_period_end": True,
            "status": "canceled",
            "metadata": {"plan_id": "starter"},
        })
        mock_event = {
            "type": "customer.subscription.deleted",
            "data": {"object": {
                "customer": "cus_cancel_001",
                "cancel_at_period_end": True,
                "status": "canceled",
                "metadata": {"plan_id": "starter"},
            }},
        }
        with patch("stripe.Webhook.construct_event", return_value=mock_event):
            resp = client.post(
                "/v1/webhooks/stripe",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "stripe-signature": _sign_webhook(payload),
                },
            )
        assert resp.status_code == 200
