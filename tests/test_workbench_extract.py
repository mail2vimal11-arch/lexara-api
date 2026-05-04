"""
Integration test for the Workbench → Portfolio bridge endpoint:
    POST /v1/workbench/session/{session_id}/extract-to-portfolio

The extractor is mocked at the SERVICE level (matching the pattern in
tests/test_portfolio_extraction_routes.py). The WorkbenchSession is
created directly in the DB so the test does not depend on commodity /
jurisdiction seed data.
"""

import uuid
from typing import Optional

import pytest
from sqlalchemy.orm import sessionmaker

from app.database.session import engine as app_engine
from app.main import app
from app.models.knowledge import WorkbenchSession
from app.routers import portfolio_routes, workbench_routes


# Wire portfolio router (matches test_portfolio_routes.py).
if not any(
    getattr(r, "path", "").startswith("/v1/portfolio")
    for r in app.router.routes
):
    app.include_router(portfolio_routes.router)


_TestSessionLocal = sessionmaker(bind=app_engine, autocommit=False, autoflush=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client) -> tuple[str, str]:
    """Returns (user_id_from_db, access_token)."""
    uid = uuid.uuid4().hex[:8]
    creds = {
        "username": f"wbx_{uid}",
        "email": f"wbx_{uid}@lexara-wbx-test.dev",
        "password": "WbxPass!2026",
    }
    r = client.post("/v1/auth/register", json=creds)
    assert r.status_code == 200, r.text
    r2 = client.post(
        "/v1/auth/login",
        json={"username": creds["username"], "password": creds["password"]},
    )
    assert r2.status_code == 200, r2.text
    token = r2.json()["access_token"]

    # Look up the user_id from the DB so we can stamp WorkbenchSession.user_id.
    from app.models.user import User
    db = _TestSessionLocal()
    try:
        user = db.query(User).filter(User.username == creds["username"]).first()
        assert user is not None
        return str(user.id), token
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_session_row(
    user_id: str,
    current_text: str,
    estimated_value_cad: Optional[float] = 250_000.0,
) -> str:
    """Insert a WorkbenchSession row directly. Returns the session_id."""
    sid = f"wb_{uuid.uuid4().hex}"
    db = _TestSessionLocal()
    try:
        s = WorkbenchSession(
            session_id=sid,
            user_id=user_id,
            jurisdiction_code="ON",
            commodity_category_code="IT_SERVICES",
            procurement_method="RFP",
            estimated_value_cad=estimated_value_cad,
            known_constraints=[],
            intent_description="test",
            current_text=current_text,
            completeness_score=0.0,
            status="active",
            template_id=None,
        )
        db.add(s)
        db.commit()
    finally:
        db.close()
    return sid


@pytest.fixture
def fake_proposals():
    return [
        {
            "obligation_type": "delivery",
            "party": "counterparty",
            "description": "Deliver the system within 30 days of contract signature.",
            "deadline_days_from_trigger": 30,
            "trigger_event": "contract_signature",
            "source_clause_text": "The Vendor shall deliver the system within 30 days...",
            "_extraction_confidence": "high",
        },
        {
            "obligation_type": "payment",
            "party": "us",
            "description": "Pay invoices within 60 days of receipt.",
            "deadline_days_from_trigger": 60,
            "trigger_event": "invoice_received",
        },
    ]


@pytest.fixture
def stub_extractor(monkeypatch, fake_proposals):
    async def _fake(sow_text, **kwargs):
        if not (sow_text or "").strip():
            return []
        return list(fake_proposals)

    # The route imports extract_obligations_from_text via portfolio_routes.
    monkeypatch.setattr(
        portfolio_routes,
        "extract_obligations_from_text",
        _fake,
    )
    return _fake


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWorkbenchExtractToPortfolio:
    def test_creates_draft_contract_and_returns_proposals(
        self, client, stub_extractor
    ):
        user_id, token = _register_and_login(client)
        sid = _create_session_row(
            user_id=user_id,
            current_text=(
                "The Vendor shall deliver the system within 30 days of contract "
                "signature. Payment is due within 60 days of invoice receipt."
            ),
        )

        r = client.post(
            f"/v1/workbench/session/{sid}/extract-to-portfolio",
            json={
                "contract_name": "Workbench-driven Contract",
                "counterparty_name": "VendorCo",
                "contract_type": "it_services",
            },
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        body = r.json()

        # Shape: {contract, extracted_count, proposals}
        assert "contract" in body
        assert "proposals" in body
        assert "extracted_count" in body
        assert body["extracted_count"] == 2
        assert len(body["proposals"]) == 2

        contract = body["contract"]
        assert contract["status"] == "draft"
        assert contract["name"] == "Workbench-driven Contract"
        assert contract["counterparty_name"] == "VendorCo"
        assert contract["contract_type"] == "it_services"
        # The session's jurisdiction_code / estimated_value_cad were threaded through.
        assert contract["jurisdiction_code"] == "ON"
        assert contract["contract_value_cad"] == 250_000.00

        # Proposal shape sanity
        first = body["proposals"][0]
        assert first["obligation_type"] == "delivery"
        assert first["party"] == "counterparty"
        assert first["description"]
        assert "id" not in first
        assert "contract_id" not in first

        # Contract is persisted as draft in the user's portfolio.
        r_get = client.get(
            f"/v1/portfolio/contracts/{contract['id']}",
            headers=_auth(token),
        )
        assert r_get.status_code == 200
        assert r_get.json()["status"] == "draft"

        # No obligations were silently saved.
        r_obls = client.get(
            f"/v1/portfolio/contracts/{contract['id']}/obligations",
            headers=_auth(token),
        )
        assert r_obls.status_code == 200
        assert r_obls.json() == []

    def test_session_with_empty_draft_400(self, client, stub_extractor):
        user_id, token = _register_and_login(client)
        sid = _create_session_row(user_id=user_id, current_text="")

        r = client.post(
            f"/v1/workbench/session/{sid}/extract-to-portfolio",
            json={
                "contract_name": "Empty Draft",
                "counterparty_name": "X",
                "contract_type": "it_services",
            },
            headers=_auth(token),
        )
        assert r.status_code == 400

    def test_unknown_session_404(self, client, stub_extractor):
        _, token = _register_and_login(client)
        r = client.post(
            "/v1/workbench/session/wb_does_not_exist/extract-to-portfolio",
            json={
                "contract_name": "Whatever",
                "counterparty_name": "X",
                "contract_type": "it_services",
            },
            headers=_auth(token),
        )
        assert r.status_code == 404

    def test_cross_user_session_403(self, client, stub_extractor):
        # User A owns the session
        user_a_id, _ = _register_and_login(client)
        sid = _create_session_row(
            user_id=user_a_id,
            current_text="Vendor shall deliver in 30 days.",
        )

        # User B tries to extract from it
        _, token_b = _register_and_login(client)
        r = client.post(
            f"/v1/workbench/session/{sid}/extract-to-portfolio",
            json={
                "contract_name": "Hijack attempt",
                "counterparty_name": "X",
                "contract_type": "it_services",
            },
            headers=_auth(token_b),
        )
        # The workbench session helper raises 403 on cross-user access.
        assert r.status_code == 403
