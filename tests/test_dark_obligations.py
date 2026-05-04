"""
Tests for the Dark Obligation Detector — /v1/dark-obligations/.

Embedding strategy for tests:
    The session-wide conftest.py replaces `embed_text` with a deterministic
    random vector based on `hash(text) % 2**32`. That makes any two distinct
    strings near-orthogonal, which would prevent a PRESENT match even when
    the SOW clearly contains the standard clause language.

    For these tests we replace `embed_text` with a tiny keyword-overlap
    embedding. Each token is hashed into one of 384 dimensions and the
    counts are L2-normalised, so two texts that share vocabulary (e.g. both
    mention "data breach notification 24 hours") cosine-correlate strongly,
    while unrelated texts stay near zero. This is fast (CPU-microseconds),
    deterministic, and exercises the real similarity / threshold / chunking
    logic of `dark_obligation_service.detect_dark_obligations`.

    The real sentence-transformers path is exercised separately in
    integration test runs.
"""

from __future__ import annotations

import re

import numpy as np
import pytest

import app.nlp.embeddings as _emb_mod
import app.services.dark_obligation_service as dos


# ── Deterministic keyword-overlap embedding (test-only) ─────────────────────

_DIM = 384
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")


def _keyword_embed(text: str) -> np.ndarray:
    vec = np.zeros(_DIM, dtype="float32")
    for tok in _TOKEN_RE.findall(text.lower()):
        if len(tok) <= 2:
            continue
        idx = hash(tok) % _DIM
        vec[idx] += 1.0
    n = np.linalg.norm(vec)
    if n > 0:
        vec /= n
    return vec


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


@pytest.fixture(autouse=True)
def _swap_embeddings(monkeypatch):
    """Use keyword-overlap embeddings inside the dark-obligation service."""
    monkeypatch.setattr(_emb_mod, "embed_text", _keyword_embed)
    monkeypatch.setattr(_emb_mod, "cosine_similarity", _cos)
    # The service imported these names at module load — patch the bindings
    # that live in dos's namespace.
    monkeypatch.setattr(dos, "embed_text", _keyword_embed)
    monkeypatch.setattr(dos, "cosine_similarity", _cos)
    yield


# ── Sample SOWs ─────────────────────────────────────────────────────────────

# An IT-services SOW that explicitly contains breach-notification language.
SOW_WITH_BREACH = """
STATEMENT OF WORK — Cloud Hosting Services

1. Services. Vendor shall provide managed cloud hosting services to the Buyer.

2. Data Breach Notification. Vendor shall notify the Buyer in writing within
24 hours of discovery of any data breach, security incident, or unauthorized
access to personal information held by Vendor on behalf of Buyer.

3. Fees. Buyer shall pay Vendor monthly in arrears within 30 days of invoice.

4. Term. This SOW is for an initial term of one year, renewable by agreement.
""" * 1  # keep length reasonable


# An IT-services SOW that has NO breach-notification or residency language.
SOW_WITHOUT_BREACH = """
STATEMENT OF WORK — Custom Software Build

1. Scope. Vendor will design and build a custom inventory tracking application
for the Buyer's warehouse operations team. Source code shall be delivered upon
completion.

2. Schedule. Phase one will complete in 12 weeks. Phase two milestones will be
agreed in writing once phase one acceptance has occurred.

3. Fees. Vendor will invoice monthly based on time-and-materials at the rates
in Schedule A.

4. Acceptance. Buyer has fifteen business days from delivery to accept or
reject any milestone deliverable.

5. Governing Law. This agreement is governed by the laws of Ontario.
"""


# ── Tests ───────────────────────────────────────────────────────────────────


class TestDetectorService:
    """Direct unit tests against the service module."""

    def test_breach_clause_marked_present(self):
        result = dos.detect_dark_obligations(
            sow_text=SOW_WITH_BREACH,
            contract_type="it_services",
            presence_threshold=0.40,  # keyword embeddings give lower scores
        )
        present_keys = {p["key"] for p in result["present"]}
        missing_keys = {m["key"] for m in result["missing"]}
        assert "data_breach_notification" in present_keys
        assert "data_breach_notification" not in missing_keys

    def test_breach_clause_flagged_when_absent(self):
        result = dos.detect_dark_obligations(
            sow_text=SOW_WITHOUT_BREACH,
            contract_type="it_services",
            presence_threshold=0.40,
        )
        missing = {m["key"]: m for m in result["missing"]}
        assert "data_breach_notification" in missing
        assert missing["data_breach_notification"]["importance"] == "critical"
        assert missing["data_breach_notification"]["peer_frequency"] >= 0.9
        assert missing["data_breach_notification"]["suggested_clause_text"]

    def test_unsupported_contract_type_returns_error_dict(self):
        result = dos.detect_dark_obligations(
            sow_text="x" * 200,
            contract_type="space_travel",
        )
        assert result["error"] == "unsupported_contract_type"
        assert "space_travel" in result["message"]
        assert "it_services" in result["supported_contract_types"]

    def test_summary_string_includes_counts(self):
        result = dos.detect_dark_obligations(
            sow_text=SOW_WITHOUT_BREACH,
            contract_type="it_services",
            presence_threshold=0.40,
        )
        assert "missing standard clause" in result["summary"]
        assert f"out of {result['checked']}" in result["summary"]


# ── HTTP / router tests ─────────────────────────────────────────────────────


class TestDetectorRoutes:
    """Tests against the FastAPI router via TestClient."""

    @pytest.fixture(autouse=True)
    def _register_router(self, client):
        """Mount the dark-obligation router for the test session.

        The instruction was 'do not edit app/main.py' — so we attach the
        router here once, at test time.
        """
        from app.main import app as _app
        from app.routers.dark_obligation_routes import router as do_router

        if not any(getattr(r, "path", "") .startswith("/v1/dark-obligations")
                   for r in _app.router.routes):
            _app.include_router(do_router)
        yield

    def test_detect_requires_auth(self, client):
        resp = client.post(
            "/v1/dark-obligations/detect",
            json={"sow_text": "x" * 500, "contract_type": "it_services"},
        )
        assert resp.status_code == 401

    def test_detect_rejects_short_sow(self, client, auth_headers):
        resp = client.post(
            "/v1/dark-obligations/detect",
            json={"sow_text": "too short", "contract_type": "it_services"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "100" in resp.json()["detail"]

    def test_detect_rejects_unsupported_type(self, client, auth_headers):
        resp = client.post(
            "/v1/dark-obligations/detect",
            json={
                "sow_text": "x" * 500,
                "contract_type": "underwater_basket_weaving",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    def test_detect_returns_expected_shape(self, client, auth_headers):
        resp = client.post(
            "/v1/dark-obligations/detect",
            json={
                "sow_text": SOW_WITHOUT_BREACH,
                "contract_type": "it_services",
                "presence_threshold": 0.40,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["contract_type"] == "it_services"
        assert isinstance(data["checked"], int) and data["checked"] > 0
        assert isinstance(data["missing"], list)
        assert isinstance(data["present"], list)
        assert isinstance(data["summary"], str)
        # Critical breach clause must be flagged for this SOW
        missing_keys = {m["key"] for m in data["missing"]}
        assert "data_breach_notification" in missing_keys

    def test_catalog_endpoint_returns_all_types(self, client, auth_headers):
        resp = client.get("/v1/dark-obligations/catalog", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for t in ("it_services", "goods", "construction", "consulting"):
            assert t in data["contract_types"]
            assert t in data["catalog"]
            assert len(data["catalog"][t]) >= 5

    def test_catalog_requires_auth(self, client):
        resp = client.get("/v1/dark-obligations/catalog")
        assert resp.status_code == 401

    def test_catalog_by_type_known(self, client, auth_headers):
        resp = client.get(
            "/v1/dark-obligations/catalog/it_services",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["contract_type"] == "it_services"
        keys = {c["key"] for c in data["clauses"]}
        assert "data_breach_notification" in keys

    def test_catalog_by_type_unknown(self, client, auth_headers):
        resp = client.get(
            "/v1/dark-obligations/catalog/martian_services",
            headers=auth_headers,
        )
        assert resp.status_code == 404
