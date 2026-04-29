"""
Tests for the Portfolio Obligation Index — /v1/portfolio.

Covers:
    - Contract create / list / get / patch / delete
    - Obligation create / list (nested + portfolio-wide)
    - Filter by obligation_type
    - Ownership isolation: user A cannot see user B's contracts/obligations
    - 404 on cross-user access for both contracts and obligations
    - Cascade delete: deleting a contract removes its obligations
"""

import uuid

import pytest

# Mount the portfolio router on the test app once per session. main.py is not
# yet wired (the human will do that), so we attach the router here so the
# integration tests can hit the endpoints through TestClient.
from app.main import app
from app.routers import portfolio_routes

if not any(
    getattr(r, "path", "").startswith("/v1/portfolio")
    for r in app.router.routes
):
    app.include_router(portfolio_routes.router)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client) -> tuple[dict, str]:
    """Register a fresh user and return (creds, access_token)."""
    uid = uuid.uuid4().hex[:8]
    creds = {
        "username": f"port_user_{uid}",
        "email": f"port_{uid}@lexara-portfolio-test.dev",
        "password": "PortfolioPass!2026",
    }
    r = client.post("/v1/auth/register", json=creds)
    assert r.status_code == 200, f"Register failed: {r.text}"
    r2 = client.post(
        "/v1/auth/login",
        json={"username": creds["username"], "password": creds["password"]},
    )
    assert r2.status_code == 200, f"Login failed: {r2.text}"
    return creds, r2.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _sample_contract_payload(name: str = "AcmeCorp Cloud SOW 2026") -> dict:
    return {
        "name": name,
        "counterparty_name": "AcmeCorp Inc.",
        "our_role": "buyer",
        "contract_type": "it_services",
        "contract_value_cad": 250_000.00,
        "currency": "CAD",
        "start_date": "2026-01-01",
        "end_date": "2027-12-31",
        "status": "active",
        "jurisdiction_code": "ON",
        "notes": "Annual cloud services renewal.",
    }


def _sample_obligation_payload(
    obligation_type: str = "payment", party: str = "us"
) -> dict:
    return {
        "obligation_type": obligation_type,
        "party": party,
        "description": "Pay invoice within 60 days of receipt.",
        "deadline_days_from_trigger": 60,
        "trigger_event": "invoice_received",
        "penalty_formula": "1.5% of contract value per day late",
        "penalty_amount_cad": 3750.00,
        "liability_cap_cad": 100_000.00,
        "source_clause_key": "payment_terms",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_a(client):
    _, token = _register_and_login(client)
    return token


@pytest.fixture
def user_b(client):
    _, token = _register_and_login(client)
    return token


# ---------------------------------------------------------------------------
# Contract CRUD
# ---------------------------------------------------------------------------

class TestContractCRUD:
    def test_create_contract(self, client, user_a):
        r = client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload(),
            headers=_auth(user_a),
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["id"]
        assert body["name"] == "AcmeCorp Cloud SOW 2026"
        assert body["counterparty_name"] == "AcmeCorp Inc."
        assert body["our_role"] == "buyer"
        assert body["contract_type"] == "it_services"
        assert body["currency"] == "CAD"
        assert body["status"] == "active"
        assert body["user_id"]

    def test_list_contracts_only_returns_own(self, client, user_a, user_b):
        # User A creates two
        client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("A-1"),
            headers=_auth(user_a),
        )
        client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("A-2"),
            headers=_auth(user_a),
        )
        # User B creates one
        client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("B-1"),
            headers=_auth(user_b),
        )

        r_a = client.get("/v1/portfolio/contracts", headers=_auth(user_a))
        assert r_a.status_code == 200
        names_a = {c["name"] for c in r_a.json()}
        assert "A-1" in names_a and "A-2" in names_a
        assert "B-1" not in names_a

        r_b = client.get("/v1/portfolio/contracts", headers=_auth(user_b))
        names_b = {c["name"] for c in r_b.json()}
        assert "B-1" in names_b
        assert "A-1" not in names_b and "A-2" not in names_b

    def test_get_contract_404_when_not_owner(self, client, user_a, user_b):
        r = client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("private-A"),
            headers=_auth(user_a),
        )
        cid = r.json()["id"]

        r_b = client.get(f"/v1/portfolio/contracts/{cid}", headers=_auth(user_b))
        assert r_b.status_code == 404

    def test_patch_contract(self, client, user_a):
        r = client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("orig-name"),
            headers=_auth(user_a),
        )
        cid = r.json()["id"]

        r2 = client.patch(
            f"/v1/portfolio/contracts/{cid}",
            json={"name": "renamed", "status": "expired"},
            headers=_auth(user_a),
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["name"] == "renamed"
        assert body["status"] == "expired"
        # Untouched fields preserved
        assert body["counterparty_name"] == "AcmeCorp Inc."

    def test_filter_by_status(self, client, user_a):
        client.post(
            "/v1/portfolio/contracts",
            json={**_sample_contract_payload("active-1"), "status": "active"},
            headers=_auth(user_a),
        )
        client.post(
            "/v1/portfolio/contracts",
            json={**_sample_contract_payload("draft-1"), "status": "draft"},
            headers=_auth(user_a),
        )

        r = client.get(
            "/v1/portfolio/contracts?status=draft", headers=_auth(user_a)
        )
        assert r.status_code == 200
        rows = r.json()
        names = {c["name"] for c in rows}
        assert "draft-1" in names
        assert "active-1" not in names


# ---------------------------------------------------------------------------
# Obligations
# ---------------------------------------------------------------------------

class TestObligations:
    def test_create_and_list_obligations(self, client, user_a):
        r = client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("oblig-host"),
            headers=_auth(user_a),
        )
        cid = r.json()["id"]

        r_obl = client.post(
            f"/v1/portfolio/contracts/{cid}/obligations",
            json=_sample_obligation_payload(),
            headers=_auth(user_a),
        )
        assert r_obl.status_code == 201, r_obl.text
        body = r_obl.json()
        assert body["contract_id"] == cid
        assert body["obligation_type"] == "payment"
        assert body["party"] == "us"
        assert body["deadline_days_from_trigger"] == 60

        r_list = client.get(
            f"/v1/portfolio/contracts/{cid}/obligations",
            headers=_auth(user_a),
        )
        assert r_list.status_code == 200
        assert len(r_list.json()) == 1

    def test_create_obligation_on_foreign_contract_404(
        self, client, user_a, user_b
    ):
        r = client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("a-only"),
            headers=_auth(user_a),
        )
        cid = r.json()["id"]

        r_b = client.post(
            f"/v1/portfolio/contracts/{cid}/obligations",
            json=_sample_obligation_payload(),
            headers=_auth(user_b),
        )
        assert r_b.status_code == 404

    def test_portfolio_wide_obligations_list_isolation(
        self, client, user_a, user_b
    ):
        # User A: 2 contracts, 3 obligations total
        ra1 = client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("a-c1"),
            headers=_auth(user_a),
        ).json()
        ra2 = client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("a-c2"),
            headers=_auth(user_a),
        ).json()
        client.post(
            f"/v1/portfolio/contracts/{ra1['id']}/obligations",
            json=_sample_obligation_payload("payment"),
            headers=_auth(user_a),
        )
        client.post(
            f"/v1/portfolio/contracts/{ra1['id']}/obligations",
            json=_sample_obligation_payload("delivery"),
            headers=_auth(user_a),
        )
        client.post(
            f"/v1/portfolio/contracts/{ra2['id']}/obligations",
            json=_sample_obligation_payload("sla"),
            headers=_auth(user_a),
        )

        # User B: 1 contract, 1 obligation
        rb1 = client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("b-c1"),
            headers=_auth(user_b),
        ).json()
        client.post(
            f"/v1/portfolio/contracts/{rb1['id']}/obligations",
            json=_sample_obligation_payload("payment"),
            headers=_auth(user_b),
        )

        r_a = client.get("/v1/portfolio/obligations", headers=_auth(user_a))
        assert r_a.status_code == 200
        rows_a = r_a.json()
        assert len(rows_a) == 3
        for o in rows_a:
            # All belong to user_a
            assert o["contract_id"] in (ra1["id"], ra2["id"])

        r_b = client.get("/v1/portfolio/obligations", headers=_auth(user_b))
        rows_b = r_b.json()
        assert len(rows_b) == 1
        assert rows_b[0]["contract_id"] == rb1["id"]

    def test_filter_by_obligation_type(self, client, user_a):
        rc = client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("filter-host"),
            headers=_auth(user_a),
        ).json()

        client.post(
            f"/v1/portfolio/contracts/{rc['id']}/obligations",
            json=_sample_obligation_payload("payment"),
            headers=_auth(user_a),
        )
        client.post(
            f"/v1/portfolio/contracts/{rc['id']}/obligations",
            json=_sample_obligation_payload("delivery"),
            headers=_auth(user_a),
        )
        client.post(
            f"/v1/portfolio/contracts/{rc['id']}/obligations",
            json=_sample_obligation_payload("sla"),
            headers=_auth(user_a),
        )

        r = client.get(
            "/v1/portfolio/obligations?obligation_type=delivery",
            headers=_auth(user_a),
        )
        assert r.status_code == 200
        rows = r.json()
        # At least one delivery; none of the wrong type
        assert len(rows) >= 1
        for o in rows:
            assert o["obligation_type"] == "delivery"

    def test_patch_obligation_cross_user_404(self, client, user_a, user_b):
        rc = client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("patch-host"),
            headers=_auth(user_a),
        ).json()
        ro = client.post(
            f"/v1/portfolio/contracts/{rc['id']}/obligations",
            json=_sample_obligation_payload(),
            headers=_auth(user_a),
        ).json()

        r = client.patch(
            f"/v1/portfolio/obligations/{ro['id']}",
            json={"description": "hijacked"},
            headers=_auth(user_b),
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Cascade delete
# ---------------------------------------------------------------------------

class TestCascadeDelete:
    def test_delete_contract_removes_obligations(self, client, user_a):
        rc = client.post(
            "/v1/portfolio/contracts",
            json=_sample_contract_payload("cascade-host"),
            headers=_auth(user_a),
        ).json()

        ro = client.post(
            f"/v1/portfolio/contracts/{rc['id']}/obligations",
            json=_sample_obligation_payload(),
            headers=_auth(user_a),
        ).json()

        # Sanity: obligation visible portfolio-wide
        before = client.get(
            "/v1/portfolio/obligations", headers=_auth(user_a)
        ).json()
        assert any(o["id"] == ro["id"] for o in before)

        # Delete the contract
        r_del = client.delete(
            f"/v1/portfolio/contracts/{rc['id']}", headers=_auth(user_a)
        )
        assert r_del.status_code == 204

        # Contract gone
        r_get = client.get(
            f"/v1/portfolio/contracts/{rc['id']}", headers=_auth(user_a)
        )
        assert r_get.status_code == 404

        # Obligation cascaded away
        after = client.get(
            "/v1/portfolio/obligations", headers=_auth(user_a)
        ).json()
        assert not any(o["id"] == ro["id"] for o in after)
