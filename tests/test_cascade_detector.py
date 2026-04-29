"""
Tests for the Cross-Contract Cascade Detector — Step 2 of the
Lexara "Blast Radius" engine.

Covers:
    - Rule A: payment-pair gap detected, with dollar quantification
    - Rule A: NO false positive when terms align (Net-30 vs Net-30)
    - Rule B: delivery slip detected at critical severity (slack ≤ 0)
    - Rule C: liability shortfall with uncovered exposure quantified
    - User isolation: A's portfolio cannot see B's contracts
    - Focus mode: per-contract cascade-check filters cleanly
    - Empty portfolio: returns zeros, not an error
    - Drafts excluded by default; included when include_draft=true
"""

import uuid

import pytest

from app.main import app
from app.routers import portfolio_routes

if not any(
    getattr(r, "path", "").startswith("/v1/portfolio")
    for r in app.router.routes
):
    app.include_router(portfolio_routes.router)


# ---------------------------------------------------------------------------
# Helpers — mirror those in test_portfolio_routes.py (kept local so the two
# test files stay independent).
# ---------------------------------------------------------------------------

def _register_and_login(client) -> str:
    uid = uuid.uuid4().hex[:8]
    creds = {
        "username": f"casc_user_{uid}",
        "email": f"casc_{uid}@lexara-cascade-test.dev",
        "password": "CascadePass!2026",
    }
    r = client.post("/v1/auth/register", json=creds)
    assert r.status_code == 200, f"Register failed: {r.text}"
    r2 = client.post(
        "/v1/auth/login",
        json={"username": creds["username"], "password": creds["password"]},
    )
    assert r2.status_code == 200, f"Login failed: {r2.text}"
    return r2.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_contract(client, token, **overrides) -> dict:
    payload = {
        "name": "default-contract",
        "counterparty_name": "DefaultCo",
        "our_role": "buyer",
        "contract_type": "it_services",
        "contract_value_cad": 100_000.00,
        "currency": "CAD",
        "status": "active",
    }
    payload.update(overrides)
    r = client.post(
        "/v1/portfolio/contracts", json=payload, headers=_auth(token)
    )
    assert r.status_code == 201, r.text
    return r.json()


def _make_obligation(client, token, contract_id, **overrides) -> dict:
    payload = {
        "obligation_type": "payment",
        "party": "us",
        "description": "default obligation",
        "deadline_days_from_trigger": 30,
        "trigger_event": "contract_start",
    }
    payload.update(overrides)
    r = client.post(
        f"/v1/portfolio/contracts/{contract_id}/obligations",
        json=payload,
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def user_a(client):
    return _register_and_login(client)


@pytest.fixture
def user_b(client):
    return _register_and_login(client)


# ---------------------------------------------------------------------------
# Rule A — Payment gap
# ---------------------------------------------------------------------------

class TestPaymentGap:
    def test_payment_gap_detected_with_quantification(self, client, user_a):
        # Prime contract: client owes us Net-60 on a $250k engagement.
        prime = _make_contract(
            client, user_a,
            name="Prime-Client",
            counterparty_name="BigClientCo",
            our_role="prime",
            contract_value_cad=250_000.00,
        )
        # Vendor contract: we owe vendor Net-30 on a $50k subcontract.
        vendor = _make_contract(
            client, user_a,
            name="Vendor-Sub",
            counterparty_name="SubVendorCo",
            our_role="buyer",
            contract_value_cad=50_000.00,
        )

        # Receivable from client: Net-60
        _make_obligation(
            client, user_a, prime["id"],
            obligation_type="payment",
            party="counterparty",
            description="Client pays us Net-60 from contract_start.",
            deadline_days_from_trigger=60,
            trigger_event="contract_start",
        )
        # Payable to vendor: Net-30
        _make_obligation(
            client, user_a, vendor["id"],
            obligation_type="payment",
            party="us",
            description="We pay vendor Net-30 from contract_start.",
            deadline_days_from_trigger=30,
            trigger_event="contract_start",
        )

        r = client.get("/v1/portfolio/cascade-check", headers=_auth(user_a))
        assert r.status_code == 200, r.text
        body = r.json()

        gaps = [c for c in body["conflicts"] if c["conflict_type"] == "payment_gap"]
        assert len(gaps) == 1, body
        g = gaps[0]
        assert g["gap_days"] == 30
        # Quantified: min(vendor.contract_value 50k, prime.contract_value 250k) = 50k
        assert g["gap_amount_cad"] == 50_000.0
        # 30 day, 50k → critical
        assert g["severity"] == "critical"
        assert "30-day" in g["narrative"] or "30 day" in g["narrative"]

        # Totals reflect this single conflict
        assert body["totals"]["total_conflicts"] == 1
        assert body["totals"]["by_severity"]["critical"] == 1
        assert body["totals"]["total_quantified_exposure_cad"] == 50_000.0
        assert body["totals"]["total_unquantified_conflicts"] == 0

    def test_no_false_positive_when_terms_align(self, client, user_a):
        # Both Net-30 → zero gap, no conflict.
        prime = _make_contract(
            client, user_a, name="Prime", counterparty_name="ClientCo",
            our_role="prime", contract_value_cad=250_000.00,
        )
        vendor = _make_contract(
            client, user_a, name="Vendor", counterparty_name="VendorCo",
            our_role="buyer", contract_value_cad=50_000.00,
        )
        _make_obligation(
            client, user_a, prime["id"],
            obligation_type="payment", party="counterparty",
            description="client Net-30",
            deadline_days_from_trigger=30,
            trigger_event="contract_start",
        )
        _make_obligation(
            client, user_a, vendor["id"],
            obligation_type="payment", party="us",
            description="vendor Net-30",
            deadline_days_from_trigger=30,
            trigger_event="contract_start",
        )

        r = client.get("/v1/portfolio/cascade-check", headers=_auth(user_a))
        body = r.json()
        gaps = [c for c in body["conflicts"] if c["conflict_type"] == "payment_gap"]
        assert gaps == []


# ---------------------------------------------------------------------------
# Rule B — Delivery slip
# ---------------------------------------------------------------------------

class TestDeliverySlip:
    def test_delivery_slip_critical_when_slack_nonpositive(self, client, user_a):
        prime = _make_contract(
            client, user_a, name="PrimeDel", counterparty_name="ClientCo",
            our_role="prime", contract_value_cad=300_000.00,
        )
        vendor = _make_contract(
            client, user_a, name="VendorDel", counterparty_name="VendorCo",
            our_role="buyer", contract_value_cad=80_000.00,
        )
        # We owe client delivery in 30 days; vendor takes 45.
        _make_obligation(
            client, user_a, prime["id"],
            obligation_type="delivery", party="us",
            description="Deliver finished system to client.",
            deadline_days_from_trigger=30,
            trigger_event="contract_start",
            penalty_amount_cad=15_000.00,
        )
        _make_obligation(
            client, user_a, vendor["id"],
            obligation_type="delivery", party="counterparty",
            description="Vendor delivers core module to us.",
            deadline_days_from_trigger=45,
            trigger_event="contract_start",
        )

        r = client.get("/v1/portfolio/cascade-check", headers=_auth(user_a))
        body = r.json()
        slips = [c for c in body["conflicts"] if c["conflict_type"] == "delivery_slip"]
        assert len(slips) == 1
        s = slips[0]
        # slack = 30 - 45 = -15
        assert s["gap_days"] == -15
        assert s["severity"] == "critical"
        assert s["gap_amount_cad"] == 15_000.0


# ---------------------------------------------------------------------------
# Rule C — Liability shortfall
# ---------------------------------------------------------------------------

class TestLiabilityShortfall:
    def test_liability_shortfall_quantified(self, client, user_a):
        # Prime contract: we owe an indemnity worth $200k.
        prime = _make_contract(
            client, user_a, name="PrimeLiab", counterparty_name="EnterpriseClient",
            our_role="prime", contract_value_cad=500_000.00,
        )
        # Vendor contract: vendor caps liability at $50k.
        vendor = _make_contract(
            client, user_a, name="VendorLiab", counterparty_name="LimitedVendor",
            our_role="buyer", contract_value_cad=80_000.00,
        )
        _make_obligation(
            client, user_a, prime["id"],
            obligation_type="indemnity", party="us",
            description="Indemnify client for IP claims.",
            penalty_amount_cad=200_000.00,
            trigger_event="ip_claim",
        )
        _make_obligation(
            client, user_a, vendor["id"],
            obligation_type="indemnity", party="counterparty",
            description="Vendor indemnifies us, capped.",
            liability_cap_cad=50_000.00,
            trigger_event="ip_claim",
        )

        r = client.get("/v1/portfolio/cascade-check", headers=_auth(user_a))
        body = r.json()
        shortfalls = [
            c for c in body["conflicts"]
            if c["conflict_type"] == "liability_shortfall"
        ]
        assert len(shortfalls) == 1
        s = shortfalls[0]
        assert s["gap_amount_cad"] == 150_000.0
        assert s["severity"] == "critical"


# ---------------------------------------------------------------------------
# User isolation + focus mode + empty portfolio + draft handling
# ---------------------------------------------------------------------------

class TestIsolationAndModes:
    def test_user_isolation(self, client, user_a, user_b):
        # User B builds a payment-gap pair. User A should never see it.
        b_prime = _make_contract(
            client, user_b, name="B-Prime", counterparty_name="BClient",
            our_role="prime", contract_value_cad=100_000.00,
        )
        b_vendor = _make_contract(
            client, user_b, name="B-Vendor", counterparty_name="BVendor",
            our_role="buyer", contract_value_cad=20_000.00,
        )
        _make_obligation(
            client, user_b, b_prime["id"],
            obligation_type="payment", party="counterparty",
            description="B client Net-60",
            deadline_days_from_trigger=60, trigger_event="contract_start",
        )
        _make_obligation(
            client, user_b, b_vendor["id"],
            obligation_type="payment", party="us",
            description="B vendor Net-30",
            deadline_days_from_trigger=30, trigger_event="contract_start",
        )

        # User A: no contracts at all.
        r_a = client.get("/v1/portfolio/cascade-check", headers=_auth(user_a))
        assert r_a.status_code == 200
        assert r_a.json()["conflicts"] == []

        # User B sees their own conflict.
        r_b = client.get("/v1/portfolio/cascade-check", headers=_auth(user_b))
        assert any(
            c["conflict_type"] == "payment_gap" for c in r_b.json()["conflicts"]
        )

    def test_focus_mode_filters_to_target_contract(self, client, user_a):
        prime = _make_contract(
            client, user_a, name="FocusPrime", counterparty_name="FocusClient",
            our_role="prime", contract_value_cad=200_000.00,
        )
        vendor = _make_contract(
            client, user_a, name="FocusVendor", counterparty_name="FocusVendorCo",
            our_role="buyer", contract_value_cad=40_000.00,
        )
        # Unrelated third contract — should be excluded when focusing on prime+vendor pair.
        unrelated = _make_contract(
            client, user_a, name="Unrelated", counterparty_name="OtherCo",
            our_role="buyer", contract_value_cad=10_000.00,
        )
        _make_obligation(
            client, user_a, prime["id"],
            obligation_type="payment", party="counterparty",
            description="Net-60 in",
            deadline_days_from_trigger=60, trigger_event="contract_start",
        )
        _make_obligation(
            client, user_a, vendor["id"],
            obligation_type="payment", party="us",
            description="Net-30 out",
            deadline_days_from_trigger=30, trigger_event="contract_start",
        )

        # Focus on the unrelated contract — no conflicts touch it.
        r = client.get(
            f"/v1/portfolio/contracts/{unrelated['id']}/cascade-check",
            headers=_auth(user_a),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["focus_contract_id"] == unrelated["id"]
        assert body["conflicts"] == []

        # Focus on the prime — exactly one payment-gap, and it touches prime.
        r2 = client.get(
            f"/v1/portfolio/contracts/{prime['id']}/cascade-check",
            headers=_auth(user_a),
        )
        body2 = r2.json()
        assert len(body2["conflicts"]) == 1
        assert any(
            ct["id"] == prime["id"] for ct in body2["conflicts"][0]["contracts"]
        )

    def test_focus_mode_404_on_foreign_contract(self, client, user_a, user_b):
        c = _make_contract(
            client, user_a, name="A-only", counterparty_name="ACo",
            our_role="prime",
        )
        r = client.get(
            f"/v1/portfolio/contracts/{c['id']}/cascade-check",
            headers=_auth(user_b),
        )
        assert r.status_code == 404

    def test_empty_portfolio_returns_zeros(self, client, user_a):
        r = client.get("/v1/portfolio/cascade-check", headers=_auth(user_a))
        assert r.status_code == 200
        body = r.json()
        assert body["conflicts"] == []
        assert body["totals"]["total_conflicts"] == 0
        assert body["totals"]["by_severity"] == {
            "critical": 0, "high": 0, "medium": 0,
        }
        assert body["totals"]["total_quantified_exposure_cad"] == 0.0
        assert body["totals"]["total_unquantified_conflicts"] == 0

    def test_drafts_excluded_by_default_included_with_flag(self, client, user_a):
        # Prime is ACTIVE; vendor is DRAFT. Pair would create a payment_gap.
        prime = _make_contract(
            client, user_a, name="DraftPrime", counterparty_name="DraftClient",
            our_role="prime", contract_value_cad=200_000.00, status="active",
        )
        vendor = _make_contract(
            client, user_a, name="DraftVendor", counterparty_name="DraftVendorCo",
            our_role="buyer", contract_value_cad=30_000.00, status="draft",
        )
        _make_obligation(
            client, user_a, prime["id"],
            obligation_type="payment", party="counterparty",
            description="Net-60 client",
            deadline_days_from_trigger=60, trigger_event="contract_start",
        )
        _make_obligation(
            client, user_a, vendor["id"],
            obligation_type="payment", party="us",
            description="Net-30 vendor",
            deadline_days_from_trigger=30, trigger_event="contract_start",
        )

        # Default: draft excluded → no conflict (only the active prime in scope).
        r = client.get("/v1/portfolio/cascade-check", headers=_auth(user_a))
        assert r.status_code == 200
        assert r.json()["conflicts"] == []

        # include_draft=true → conflict appears.
        r2 = client.get(
            "/v1/portfolio/cascade-check?include_draft=true",
            headers=_auth(user_a),
        )
        body2 = r2.json()
        gaps = [c for c in body2["conflicts"] if c["conflict_type"] == "payment_gap"]
        assert len(gaps) == 1
