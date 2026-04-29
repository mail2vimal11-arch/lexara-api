"""
Integration tests for the LLM-powered portfolio extraction routes.

Covers the three new endpoints:
    POST /v1/portfolio/contracts/{id}/extract-obligations
    POST /v1/portfolio/contracts/{id}/obligations/batch-create
    POST /v1/portfolio/extract-and-stage

The extractor is mocked at the SERVICE level (not the LLM level) so these
tests stay fast and deterministic, and so we don't have to rebuild prompts
to change the test fixtures.
"""

import uuid

import pytest

from app.main import app
from app.routers import portfolio_routes

# Make sure the portfolio router is mounted (matches the pattern used in
# tests/test_portfolio_routes.py).
if not any(
    getattr(r, "path", "").startswith("/v1/portfolio")
    for r in app.router.routes
):
    app.include_router(portfolio_routes.router)


# ---------------------------------------------------------------------------
# Helpers — match the style of test_portfolio_routes.py
# ---------------------------------------------------------------------------

def _register_and_login(client) -> str:
    uid = uuid.uuid4().hex[:8]
    creds = {
        "username": f"extract_{uid}",
        "email": f"extract_{uid}@lexara-extract-test.dev",
        "password": "ExtractPass!2026",
    }
    r = client.post("/v1/auth/register", json=creds)
    assert r.status_code == 200, r.text
    r2 = client.post(
        "/v1/auth/login",
        json={"username": creds["username"], "password": creds["password"]},
    )
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _contract_payload(name: str = "Extract Host Contract") -> dict:
    return {
        "name": name,
        "counterparty_name": "ExtractCo Ltd.",
        "our_role": "buyer",
        "contract_type": "it_services",
        "contract_value_cad": 100_000.00,
        "currency": "CAD",
        "status": "active",
        "jurisdiction_code": "ON",
    }


@pytest.fixture
def user_a(client):
    return _register_and_login(client)


@pytest.fixture
def user_b(client):
    return _register_and_login(client)


@pytest.fixture
def fake_proposals():
    return [
        {
            "obligation_type": "payment",
            "party": "us",
            "description": "Pay vendor invoices within 60 days of receipt.",
            "deadline_days_from_trigger": 60,
            "trigger_event": "invoice_received",
            "source_clause_text": "Vendor shall pay invoices within 60 days of receipt.",
            "_extraction_confidence": "high",
        },
        {
            "obligation_type": "delivery",
            "party": "counterparty",
            "description": "Deliver migrated system within 30 days of contract signature.",
            "deadline_days_from_trigger": 30,
            "trigger_event": "contract_signature",
        },
    ]


@pytest.fixture
def stub_extractor(monkeypatch, fake_proposals):
    """Mock the extractor at the service level so the route doesn't hit the
    LLM stack at all."""
    async def _fake(sow_text, **kwargs):
        # When called with empty text, return nothing.
        if not (sow_text or "").strip():
            return []
        return list(fake_proposals)

    monkeypatch.setattr(
        portfolio_routes,
        "extract_obligations_from_text",
        _fake,
    )
    return _fake


# ---------------------------------------------------------------------------
# extract-obligations endpoint
# ---------------------------------------------------------------------------

class TestExtractObligations:
    def test_returns_proposals_without_persisting(
        self, client, user_a, stub_extractor
    ):
        rc = client.post(
            "/v1/portfolio/contracts",
            json=_contract_payload("extract-target"),
            headers=_auth(user_a),
        ).json()

        r = client.post(
            f"/v1/portfolio/contracts/{rc['id']}/extract-obligations",
            json={"sow_text": "Vendor shall pay invoices within 60 days."},
            headers=_auth(user_a),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["contract_id"] == rc["id"]
        assert body["extracted_count"] == 2
        assert len(body["proposals"]) == 2
        assert body["proposals"][0]["obligation_type"] == "payment"

        # Proposals carry the UI hint when present
        assert body["proposals"][0].get("_extraction_confidence") == "high"

        # CRITICAL: nothing was persisted. The portfolio-wide obligations list
        # for this user should still be empty.
        r_list = client.get(
            "/v1/portfolio/obligations", headers=_auth(user_a)
        )
        assert r_list.status_code == 200
        assert r_list.json() == []

        # Sanity: per-contract list is also empty.
        r_per_contract = client.get(
            f"/v1/portfolio/contracts/{rc['id']}/obligations",
            headers=_auth(user_a),
        )
        assert r_per_contract.status_code == 200
        assert r_per_contract.json() == []

    def test_cross_user_404(self, client, user_a, user_b, stub_extractor):
        rc = client.post(
            "/v1/portfolio/contracts",
            json=_contract_payload("private-extract"),
            headers=_auth(user_a),
        ).json()

        r = client.post(
            f"/v1/portfolio/contracts/{rc['id']}/extract-obligations",
            json={"sow_text": "anything"},
            headers=_auth(user_b),
        )
        assert r.status_code == 404

    def test_unknown_contract_404(self, client, user_a, stub_extractor):
        r = client.post(
            "/v1/portfolio/contracts/does-not-exist/extract-obligations",
            json={"sow_text": "anything"},
            headers=_auth(user_a),
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# batch-create endpoint
# ---------------------------------------------------------------------------

class TestBatchCreate:
    def test_persists_multiple_atomically(self, client, user_a):
        rc = client.post(
            "/v1/portfolio/contracts",
            json=_contract_payload("batch-host"),
            headers=_auth(user_a),
        ).json()

        payload = {
            "obligations": [
                {
                    "obligation_type": "payment",
                    "party": "us",
                    "description": "Pay invoice within 60 days.",
                    "deadline_days_from_trigger": 60,
                    "trigger_event": "invoice_received",
                },
                {
                    "obligation_type": "delivery",
                    "party": "counterparty",
                    "description": "Deliver milestone 1.",
                    "deadline_days_from_trigger": 30,
                },
                {
                    "obligation_type": "sla",
                    "party": "counterparty",
                    "description": "Maintain 99.9% monthly uptime.",
                },
            ]
        }
        r = client.post(
            f"/v1/portfolio/contracts/{rc['id']}/obligations/batch-create",
            json=payload,
            headers=_auth(user_a),
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["created_count"] == 3
        assert len(body["obligation_ids"]) == 3
        assert len(body["obligations"]) == 3

        # Verify they actually landed in the DB
        r_list = client.get(
            f"/v1/portfolio/contracts/{rc['id']}/obligations",
            headers=_auth(user_a),
        )
        assert r_list.status_code == 200
        rows = r_list.json()
        assert len(rows) == 3
        types = {o["obligation_type"] for o in rows}
        assert types == {"payment", "delivery", "sla"}

    def test_bad_obligation_in_batch_rolls_back_all(self, client, user_a):
        rc = client.post(
            "/v1/portfolio/contracts",
            json=_contract_payload("rollback-host"),
            headers=_auth(user_a),
        ).json()

        # Pre-existing obligation count for this contract: 0
        before = client.get(
            f"/v1/portfolio/contracts/{rc['id']}/obligations",
            headers=_auth(user_a),
        ).json()
        assert before == []

        payload = {
            "obligations": [
                {
                    "obligation_type": "payment",
                    "party": "us",
                    "description": "Good obligation.",
                },
                {
                    # Invalid obligation_type — this should torch the whole batch.
                    "obligation_type": "carrier_pigeon",
                    "party": "us",
                    "description": "Bad obligation.",
                },
            ]
        }
        r = client.post(
            f"/v1/portfolio/contracts/{rc['id']}/obligations/batch-create",
            json=payload,
            headers=_auth(user_a),
        )
        assert r.status_code == 400, r.text

        # Atomic rollback: not even the good one should have persisted.
        after = client.get(
            f"/v1/portfolio/contracts/{rc['id']}/obligations",
            headers=_auth(user_a),
        ).json()
        assert after == []

    def test_empty_batch_400(self, client, user_a):
        rc = client.post(
            "/v1/portfolio/contracts",
            json=_contract_payload("empty-batch-host"),
            headers=_auth(user_a),
        ).json()

        r = client.post(
            f"/v1/portfolio/contracts/{rc['id']}/obligations/batch-create",
            json={"obligations": []},
            headers=_auth(user_a),
        )
        assert r.status_code == 400

    def test_batch_create_cross_user_404(self, client, user_a, user_b):
        rc = client.post(
            "/v1/portfolio/contracts",
            json=_contract_payload("cross-batch"),
            headers=_auth(user_a),
        ).json()

        payload = {
            "obligations": [
                {
                    "obligation_type": "payment",
                    "party": "us",
                    "description": "Pay.",
                }
            ]
        }
        r = client.post(
            f"/v1/portfolio/contracts/{rc['id']}/obligations/batch-create",
            json=payload,
            headers=_auth(user_b),
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# extract-and-stage endpoint
# ---------------------------------------------------------------------------

class TestExtractAndStage:
    def test_creates_draft_contract_and_returns_proposals(
        self, client, user_a, stub_extractor
    ):
        payload = {
            "sow_text": "The Vendor shall pay invoices within 60 days.",
            "contract_type": "it_services",
            "contract_name": "AcmeCorp Migration",
            "counterparty_name": "AcmeCorp Inc.",
            "contract_value_cad": 500_000.00,
            "jurisdiction_code": "ON",
        }
        r = client.post(
            "/v1/portfolio/extract-and-stage",
            json=payload,
            headers=_auth(user_a),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["extracted_count"] == 2
        assert len(body["proposals"]) == 2

        contract = body["contract"]
        assert contract["status"] == "draft"
        assert contract["name"] == "AcmeCorp Migration"
        assert contract["counterparty_name"] == "AcmeCorp Inc."
        assert contract["contract_type"] == "it_services"

        # Contract was actually saved (status=draft).
        r_get = client.get(
            f"/v1/portfolio/contracts/{contract['id']}",
            headers=_auth(user_a),
        )
        assert r_get.status_code == 200
        assert r_get.json()["status"] == "draft"

        # No obligations persisted — proposals are review-only.
        r_obls = client.get(
            f"/v1/portfolio/contracts/{contract['id']}/obligations",
            headers=_auth(user_a),
        )
        assert r_obls.status_code == 200
        assert r_obls.json() == []

    def test_extract_and_stage_minimal_payload(
        self, client, user_a, stub_extractor
    ):
        """contract_name / counterparty_name are optional — sensible defaults
        should kick in."""
        r = client.post(
            "/v1/portfolio/extract-and-stage",
            json={
                "sow_text": "Vendor shall do something within 14 days.",
                "contract_type": "consulting",
            },
            headers=_auth(user_a),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Sensible defaults so the contract row passes NOT NULL.
        assert body["contract"]["name"]
        assert body["contract"]["counterparty_name"]
        assert body["contract"]["status"] == "draft"
        assert body["extracted_count"] == 2
