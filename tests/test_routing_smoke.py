"""
Routing smoke tests for Feature 2 (SOW Workbench) and Feature 6 (Negotiation
Simulator). These guard against prefix-duplication bugs and broken auth
exemptions that the existing functional suite does not exercise.
"""

from app.main import app


# ── Helpers ─────────────────────────────────────────────────────────────────

def _registered_paths() -> set[str]:
    return {r.path for r in app.routes if hasattr(r, "methods")}


# ── Feature 6: negotiation routes are mounted at /v1/negotiation/* ──────────

EXPECTED_NEGOTIATION_PATHS = {
    "/v1/negotiation/start",
    "/v1/negotiation/{session_id}",
    "/v1/negotiation/{session_id}/propose",
    "/v1/negotiation/{session_id}/respond",
    "/v1/negotiation/{session_id}/trade",
    "/v1/negotiation/{session_id}/batna",
    "/v1/negotiation/{session_id}/scenario",
    "/v1/negotiation/{session_id}/ledger",
    "/v1/negotiation/{session_id}/invite",
    "/v1/negotiation/join/{token}",
    "/v1/negotiation/{session_id}/export",
}


def test_negotiation_routes_have_canonical_prefix():
    """Every Feature 6 endpoint must serve at /v1/negotiation/*, not the
    duplicated /v1/negotiation/v1/negotiation/* path that ships if a router-level
    prefix is reintroduced alongside main.py's include_router prefix."""
    paths = _registered_paths()
    missing = EXPECTED_NEGOTIATION_PATHS - paths
    assert not missing, f"Negotiation routes missing at canonical prefix: {missing}"


def test_no_duplicated_negotiation_prefix():
    paths = _registered_paths()
    duplicated = {p for p in paths if p.startswith("/v1/negotiation/v1/negotiation")}
    assert not duplicated, f"Duplicated /v1/negotiation prefix detected: {duplicated}"


def test_negotiation_start_requires_auth(client):
    """A protected route with no token must hit the middleware and return 401.
    The route inspection test above guards the path; this guards that the
    middleware actually fires for it."""
    resp = client.post("/v1/negotiation/start", json={})
    assert resp.status_code == 401, (
        f"/v1/negotiation/start should require auth: got {resp.status_code} {resp.text}"
    )


# ── Feature 2: workbench public catalogue ───────────────────────────────────

def test_workbench_commodities_is_public(client):
    """GET /v1/workbench/commodities is in UNPROTECTED_ROUTES — must not 401
    without a Bearer token. Empty result on a fresh DB is fine; the contract
    being tested here is reachability, not seeded content."""
    resp = client.get("/v1/workbench/commodities")
    assert resp.status_code == 200, f"{resp.status_code} {resp.text}"


def test_workbench_jurisdictions_is_public(client):
    resp = client.get("/v1/workbench/jurisdictions")
    assert resp.status_code == 200, f"{resp.status_code} {resp.text}"


def test_workbench_session_requires_auth(client):
    resp = client.post("/v1/workbench/session", json={})
    assert resp.status_code == 401, f"{resp.status_code} {resp.text}"
