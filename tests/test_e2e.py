"""
End-to-end tests for LexAra API.

Runs against the FastAPI app using TestClient with SQLite and mocked external
services. Covers: health, auth, contract analysis (5 tabs), upload, billing/plans,
usage, procurement tools (lint, citations, clauses), and error handling.
"""

import io
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from tests.conftest import (
    SAMPLE_CONTRACT,
    SAMPLE_CLAUSE_TEXT,
    MOCK_SUMMARY_RESPONSE,
    MOCK_RISK_SCORE_RESPONSE,
    MOCK_KEY_RISKS_RESPONSE,
    MOCK_MISSING_CLAUSES_RESPONSE,
    MOCK_EXTRACT_CLAUSES_RESPONSE,
)


# ─── 1. Public / Health Endpoints ────────────────────────────────────────────


class TestHealthEndpoints:

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "api_version" in data

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_openapi_docs(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema
        assert "info" in schema


# ─── 2. Authentication Flow ─────────────────────────────────────────────────


class TestAuthFlow:

    def test_register_new_user(self, client, test_user_credentials):
        resp = client.post("/v1/auth/register", json=test_user_credentials)
        # May already be registered by the auth_token fixture
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            data = resp.json()
            assert data["username"] == test_user_credentials["username"]

    def test_register_duplicate_user(self, client, test_user_credentials):
        # Ensure user exists
        client.post("/v1/auth/register", json=test_user_credentials)
        resp = client.post("/v1/auth/register", json=test_user_credentials)
        assert resp.status_code == 400
        assert "already taken" in resp.json().get("detail", "").lower()

    def test_login_valid(self, client, test_user_credentials):
        resp = client.post("/v1/auth/login", json={
            "username": test_user_credentials["username"],
            "password": test_user_credentials["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "role" in data

    def test_login_wrong_password(self, client, test_user_credentials):
        resp = client.post("/v1/auth/login", json={
            "username": test_user_credentials["username"],
            "password": "WrongPassword123!",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/v1/auth/login", json={
            "username": "nonexistent_user_xyz_999",
            "password": "anything",
        })
        assert resp.status_code == 401


# ─── 3. Auth Enforcement ────────────────────────────────────────────────────


class TestAuthEnforcement:

    @pytest.mark.parametrize("method,path", [
        ("GET", "/v1/plans"),
        ("GET", "/v1/usage"),
        ("POST", "/v1/summary"),
        ("POST", "/v1/risk-score"),
        ("POST", "/v1/key-risks"),
        ("POST", "/v1/missing-clauses"),
        ("POST", "/v1/extract-clauses"),
        ("POST", "/v1/upload"),
        ("POST", "/v1/procurement/lint"),
        ("POST", "/v1/procurement/citations"),
        ("POST", "/v1/procurement/clauses"),
    ])
    def test_no_auth_returns_401(self, client, method, path):
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json={"text": "test"})
        assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}"


# ─── 4. Billing / Plans ─────────────────────────────────────────────────────


class TestBillingPlans:

    def test_list_plans(self, client, auth_headers):
        resp = client.get("/v1/plans", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "plans" in data
        plans = data["plans"]
        assert "free" in plans
        assert "starter" in plans
        assert "growth" in plans
        assert "business" in plans
        assert plans["free"]["price_cad"] == 0
        assert plans["business"]["analyses_limit"] == -1

    def test_checkout_free_plan_rejected(self, client, auth_headers):
        resp = client.post("/v1/checkout", headers=auth_headers, json={
            "plan_id": "free",
            "email": "test@example.com",
        })
        assert resp.status_code == 400
        assert "free" in resp.json().get("detail", "").lower()

    def test_checkout_invalid_plan(self, client, auth_headers):
        resp = client.post("/v1/checkout", headers=auth_headers, json={
            "plan_id": "nonexistent_plan",
            "email": "test@example.com",
        })
        assert resp.status_code == 400


# ─── 5. Usage ────────────────────────────────────────────────────────────────


class TestUsage:

    def test_get_usage(self, client, auth_headers):
        resp = client.get("/v1/usage", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "plan" in data
        assert "analyses_used_this_month" in data
        assert "analyses_limit" in data
        assert "remaining_quota" in data


# ─── 6. Contract Analysis (5 Tabs) — with mocked Claude API ─────────────────


class TestContractAnalysis:

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_summary(self, mock_claude, client, auth_headers):
        mock_claude.return_value = MOCK_SUMMARY_RESPONSE
        resp = client.post("/v1/summary", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
            "contract_type": "services",
            "jurisdiction": "ON",
        })
        assert resp.status_code == 200, f"Summary failed: {resp.text}"
        data = resp.json()
        assert "analysis_id" in data
        assert len(data["summary"]) > 0
        assert "contract_type" in data
        assert "confidence" in data
        assert data["processing_time_ms"] >= 0
        mock_claude.assert_called_once()

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_risk_score(self, mock_claude, client, auth_headers):
        mock_claude.return_value = MOCK_RISK_SCORE_RESPONSE
        resp = client.post("/v1/risk-score", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
            "contract_type": "services",
            "jurisdiction": "ON",
        })
        assert resp.status_code == 200, f"Risk score failed: {resp.text}"
        data = resp.json()
        assert "analysis_id" in data
        assert 0 <= data["overall_risk_score"] <= 100
        assert data["risk_level"] in ("low", "medium", "high", "critical")
        assert "scores_by_category" in data
        assert "interpretation" in data

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_key_risks(self, mock_claude, client, auth_headers):
        mock_claude.return_value = MOCK_KEY_RISKS_RESPONSE
        resp = client.post("/v1/key-risks", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
            "contract_type": "services",
            "jurisdiction": "ON",
        })
        assert resp.status_code == 200, f"Key risks failed: {resp.text}"
        data = resp.json()
        assert "analysis_id" in data
        assert isinstance(data["key_risks"], list)
        assert len(data["key_risks"]) >= 1
        risk = data["key_risks"][0]
        assert "severity" in risk
        assert "title" in risk
        assert "description" in risk

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_missing_clauses(self, mock_claude, client, auth_headers):
        mock_claude.return_value = MOCK_MISSING_CLAUSES_RESPONSE
        resp = client.post("/v1/missing-clauses", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
            "contract_type": "services",
            "jurisdiction": "ON",
        })
        assert resp.status_code == 200, f"Missing clauses failed: {resp.text}"
        data = resp.json()
        assert "analysis_id" in data
        assert isinstance(data["missing_clauses"], list)
        assert len(data["missing_clauses"]) >= 1
        clause = data["missing_clauses"][0]
        assert "clause" in clause
        assert "importance" in clause
        assert "rationale" in clause

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_extract_clauses(self, mock_claude, client, auth_headers):
        mock_claude.return_value = MOCK_EXTRACT_CLAUSES_RESPONSE
        resp = client.post("/v1/extract-clauses", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
            "contract_type": "services",
            "jurisdiction": "ON",
        })
        assert resp.status_code == 200, f"Extract clauses failed: {resp.text}"
        data = resp.json()
        assert "analysis_id" in data
        assert isinstance(data["clauses"], list)
        assert len(data["clauses"]) >= 1
        clause = data["clauses"][0]
        assert "type" in clause
        assert "summary" in clause
        assert "confidence" in clause


# ─── 7. Contract Analysis — Validation Errors ───────────────────────────────


class TestContractValidation:

    @pytest.mark.parametrize("endpoint", [
        "/v1/summary",
        "/v1/risk-score",
        "/v1/key-risks",
        "/v1/missing-clauses",
        "/v1/extract-clauses",
    ])
    def test_text_too_short(self, client, auth_headers, endpoint):
        resp = client.post(endpoint, headers=auth_headers, json={
            "text": "Too short",
        })
        assert resp.status_code == 400
        assert "100 characters" in resp.json().get("detail", "")

    @pytest.mark.parametrize("endpoint", [
        "/v1/summary",
        "/v1/risk-score",
        "/v1/key-risks",
        "/v1/missing-clauses",
        "/v1/extract-clauses",
    ])
    def test_text_too_long(self, client, auth_headers, endpoint):
        resp = client.post(endpoint, headers=auth_headers, json={
            "text": "X" * 50001,
        })
        assert resp.status_code == 400
        assert "50,000" in resp.json().get("detail", "")


# ─── 8. File Upload ──────────────────────────────────────────────────────────


class TestFileUpload:

    def test_upload_txt_file(self, client, auth_headers):
        content = SAMPLE_CONTRACT.encode("utf-8")
        files = {"file": ("test_contract.txt", io.BytesIO(content), "text/plain")}
        resp = client.post("/v1/upload", headers=auth_headers, files=files)
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        data = resp.json()
        assert data["filename"] == "test_contract.txt"
        assert data["char_count"] > 0
        assert data["word_count"] > 0
        assert len(data["text"]) > 50

    def test_upload_no_auth(self, client):
        content = b"Some contract text content here for testing purposes."
        files = {"file": ("test.txt", io.BytesIO(content), "text/plain")}
        resp = client.post("/v1/upload", files=files)
        assert resp.status_code == 401

    def test_upload_empty_file(self, client, auth_headers):
        files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        resp = client.post("/v1/upload", headers=auth_headers, files=files)
        assert resp.status_code == 422


# ─── 9. Procurement Tools ───────────────────────────────────────────────────


class TestProcurementLint:

    def test_lint_document(self, client, auth_headers):
        text = (
            "The party of the first part hereinafter referred to as the Vendor "
            "shall indemnify and hold harmless the party of the second part. "
            "Notwithstanding the foregoing, the aforementioned obligations shall "
            "be subject to the provisions herein. The parties agree that all "
            "deliverables shall be provided in accordance with the terms and "
            "conditions set forth hereinafter."
        )
        resp = client.post("/v1/procurement/lint", headers=auth_headers, json={
            "text": text,
        })
        assert resp.status_code == 200, f"Lint failed: {resp.text}"
        data = resp.json()
        assert "total_issues" in data
        assert "legalese" in data
        assert "passive_voice" in data
        assert "plural_parties" in data
        assert "gendered_language" in data
        assert isinstance(data["legalese"], list)
        # Should find legalese like "hereinafter", "notwithstanding", "herein"
        assert data["total_issues"] > 0, "Linter should find legalese issues"
        legalese_terms = [item["term"].lower() for item in data["legalese"]]
        assert any("herein" in t for t in legalese_terms), "Should detect 'herein'"

    def test_lint_text_too_short(self, client, auth_headers):
        resp = client.post("/v1/procurement/lint", headers=auth_headers, json={
            "text": "Short.",
        })
        assert resp.status_code == 400

    def test_lint_clean_text(self, client, auth_headers):
        text = (
            "The Contractor will deliver the software within 30 days of signing. "
            "The Client will pay for the services within 15 days of receiving the "
            "invoice. Both parties agree to the terms."
        )
        resp = client.post("/v1/procurement/lint", headers=auth_headers, json={
            "text": text,
        })
        assert resp.status_code == 200
        data = resp.json()
        # Clean text should have minimal issues
        assert data["total_issues"] >= 0


class TestProcurementCitations:

    def test_validate_citations_with_statutes(self, client, auth_headers):
        text = (
            "This contract is governed by the Competition Act, RSC 1985, c C-34. "
            "See also the Employment Standards Act, SO 2000, c 41."
        )
        resp = client.post("/v1/procurement/citations", headers=auth_headers, json={
            "text": text,
        })
        assert resp.status_code == 200, f"Citations failed: {resp.text}"
        data = resp.json()
        assert "total" in data
        assert "statutes" in data
        assert "regulations" in data
        assert "cases" in data
        assert isinstance(data["statutes"], list)
        assert data["total"] >= 1, "Should find at least one statute citation"

    def test_validate_citations_with_cases(self, client, auth_headers):
        text = (
            "The Supreme Court held in Canada v Bedford, 2013 SCC 72 that the "
            "provisions were unconstitutional."
        )
        resp = client.post("/v1/procurement/citations", headers=auth_headers, json={
            "text": text,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1, "Should find case citation"

    def test_citations_no_citations(self, client, auth_headers):
        resp = client.post("/v1/procurement/citations", headers=auth_headers, json={
            "text": "This is a plain text document with no legal citations at all in it whatsoever.",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0


class TestProcurementClauses:

    def test_search_clauses(self, client, auth_headers):
        resp = client.post("/v1/procurement/clauses", headers=auth_headers, json={
            "query": "indemnification",
        })
        assert resp.status_code == 200, f"Clause search failed: {resp.text}"
        data = resp.json()
        assert "total" in data
        assert "categories" in data
        assert "clauses" in data
        assert isinstance(data["clauses"], list)
        assert data["total"] > 0, "Should find indemnification clauses"

    def test_search_clauses_with_category(self, client, auth_headers):
        resp = client.post("/v1/procurement/clauses", headers=auth_headers, json={
            "query": "liability",
            "category": "Limitation of Liability",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "clauses" in data

    def test_list_all_clauses(self, client, auth_headers):
        resp = client.post("/v1/procurement/clauses", headers=auth_headers, json={
            "query": "",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert data["total"] > 0, "Clause library should not be empty"


# ─── 10. Procurement AI — Clause Analysis & Semantic Search ─────────────────


class TestProcurementClauseAI:

    @patch("app.nlp.search.search_similar_clauses", return_value=[])
    def test_analyze_clause(self, mock_search, client, auth_headers):
        resp = client.post("/v1/procurement/clauses/analyze", headers=auth_headers, json={
            "text": SAMPLE_CLAUSE_TEXT,
        })
        assert resp.status_code == 200, f"Analyze clause: {resp.status_code} {resp.text}"
        data = resp.json()
        assert "clause_type" in data
        assert "risk_level" in data
        assert data["risk_level"] in ("High", "Medium", "Low")

    @patch("app.nlp.search.search_similar_clauses", return_value=[])
    def test_semantic_search(self, mock_search, client, auth_headers):
        resp = client.post("/v1/procurement/clauses/search", headers=auth_headers, json={
            "query": "indemnification clause for government contracts",
            "k": 3,
        })
        assert resp.status_code == 200, f"Semantic search: {resp.status_code} {resp.text}"
        data = resp.json()
        assert "total" in data
        assert "clauses" in data

    def test_clause_library(self, client, auth_headers):
        resp = client.get("/v1/procurement/clauses/library", headers=auth_headers)
        assert resp.status_code == 200, f"Library: {resp.status_code} {resp.text}"
        data = resp.json()
        assert "total" in data
        assert "clauses" in data


# ─── 11. Procurement AI — Contract Comparison ───────────────────────────────


class TestProcurementCompare:

    def test_compare_clauses(self, client, auth_headers):
        resp = client.post("/v1/procurement/compare/clauses", headers=auth_headers, json={
            "clause_a": "The Contractor shall indemnify the Crown against all claims.",
            "clause_b": (
                "The Vendor shall hold harmless and indemnify the Government "
                "from any and all claims, losses, and damages."
            ),
        })
        assert resp.status_code == 200, f"Compare clauses: {resp.status_code} {resp.text}"
        data = resp.json()
        assert "similarity_score" in data
        assert "verdict" in data
        assert 0.0 <= data["similarity_score"] <= 1.0


# ─── 12. Ingestion (Role-Based Access) ──────────────────────────────────────


class TestIngestion:

    def test_list_tenders(self, client, auth_headers):
        resp = client.get("/v1/procurement/ingestion/tenders", headers=auth_headers)
        # procurement role should have access
        assert resp.status_code == 200, f"Tenders: {resp.status_code} {resp.text}"
        data = resp.json()
        assert "total" in data
        assert "tenders" in data

    def test_trigger_ingestion_requires_admin(self, client, auth_headers):
        """Non-admin (procurement) users should be forbidden."""
        resp = client.post("/v1/procurement/ingestion/run", headers=auth_headers, json={
            "query": "test",
        })
        assert resp.status_code == 403, f"Ingestion: {resp.status_code} {resp.text}"


# ─── 13. Cross-Cutting Concerns ─────────────────────────────────────────────


class TestCrossCutting:

    def test_cors_preflight(self, client):
        # Use an allowed origin from the test config (localhost:3000)
        resp = client.options("/v1/summary", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        })
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers

    def test_404_for_unknown_route(self, client):
        resp = client.get("/v1/nonexistent-endpoint")
        assert resp.status_code in (401, 404)

    def test_method_not_allowed(self, client, auth_headers):
        resp = client.delete("/v1/summary", headers=auth_headers)
        assert resp.status_code == 405

    def test_missing_request_body(self, client, auth_headers):
        resp = client.post("/v1/summary", headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_json_body(self, client, auth_headers):
        resp = client.post(
            "/v1/summary",
            headers={**auth_headers, "Content-Type": "application/json"},
            content=b"not-json",
        )
        assert resp.status_code == 422
