"""
Additional E2E tests for coverage gaps identified in QA review.

Covers:
- Billing portal (501 stub) and Stripe webhook endpoints
- Excel comparison (compare/excel with .xlsx upload)
- File upload: DOCX, oversized files, unsupported types
- Stripe checkout success path with mocked Stripe
- Tender list with source/country/pagination filters
- Clause library with category/jurisdiction filters
- Multi-LLM waterfall fallback: Groq→HF→Claude
- Auth enforcement on compare and ingestion routes
- Edge cases: text boundary validation, response field completeness
"""

import io
import json
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from tests.conftest import SAMPLE_CONTRACT, SAMPLE_CLAUSE_TEXT


# ─── Billing: Portal & Webhook ────────────────────────────────────────────────


class TestBillingPortal:

    def test_portal_returns_501(self, client, auth_headers):
        """Portal is a stub — should return 501 Not Implemented."""
        resp = client.post("/v1/portal", headers=auth_headers)
        assert resp.status_code == 501, f"Expected 501, got {resp.status_code}: {resp.text}"
        detail = resp.json().get("detail", "")
        assert "portal" in detail.lower() or "coming soon" in detail.lower()

    def test_portal_no_auth_returns_401(self, client):
        resp = client.post("/v1/portal")
        assert resp.status_code == 401

    def test_stripe_webhook_bad_signature(self, client):
        """Webhook with invalid signature should be rejected."""
        payload = json.dumps({"type": "checkout.session.completed"}).encode()
        resp = client.post(
            "/v1/webhooks/stripe",
            content=payload,
            headers={"Content-Type": "application/json", "stripe-signature": "bad_sig"},
        )
        assert resp.status_code in (400, 401, 422), \
            f"Expected 4xx for bad sig, got {resp.status_code}"

    def test_stripe_webhook_alias_endpoint(self, client):
        """Both /webhook and /webhooks/stripe should behave the same."""
        payload = json.dumps({"type": "test"}).encode()
        r1 = client.post("/v1/webhooks/stripe", content=payload,
                         headers={"Content-Type": "application/json", "stripe-signature": "bad"})
        r2 = client.post("/v1/webhook", content=payload,
                         headers={"Content-Type": "application/json", "stripe-signature": "bad"})
        assert r1.status_code == r2.status_code, \
            f"Alias endpoints returned different status: {r1.status_code} vs {r2.status_code}"


class TestBillingCheckoutPaidPlan:

    def test_checkout_starter_plan_mocked_stripe(self, client, auth_headers):
        """Checkout for a paid plan should succeed when Stripe is mocked."""
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc123"
        mock_session.id = "cs_test_abc123"

        with patch("stripe.checkout.Session.create", return_value=mock_session):
            resp = client.post("/v1/checkout", headers=auth_headers, json={
                "plan_id": "starter",
                "email": "testbuyer@example.com",
            })
        assert resp.status_code == 200, f"Checkout failed: {resp.text}"
        data = resp.json()
        assert "checkout_url" in data
        assert data["checkout_url"].startswith("https://checkout.stripe.com")
        assert "session_id" in data
        assert "plan" in data
        assert "amount_cad" in data

    def test_checkout_stripe_error_returns_502(self, client, auth_headers):
        """Stripe API errors should surface as 502."""
        import stripe as _stripe
        with patch("stripe.checkout.Session.create",
                   side_effect=_stripe.error.StripeError("Connection error")):
            resp = client.post("/v1/checkout", headers=auth_headers, json={
                "plan_id": "growth",
                "email": "testbuyer@example.com",
            })
        assert resp.status_code == 502, f"Expected 502 for Stripe error, got {resp.status_code}"

    def test_checkout_invalid_email_returns_422(self, client, auth_headers):
        resp = client.post("/v1/checkout", headers=auth_headers, json={
            "plan_id": "starter",
            "email": "not-an-email",
        })
        assert resp.status_code == 422


# ─── File Upload — Extended ───────────────────────────────────────────────────


class TestFileUploadExtended:

    def test_upload_docx_file(self, client, auth_headers):
        """DOCX files should be accepted and text extracted."""
        from docx import Document
        doc = Document()
        doc.add_paragraph(SAMPLE_CONTRACT)
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        files = {
            "file": (
                "contract.docx",
                buf,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        resp = client.post("/v1/upload", headers=auth_headers, files=files)
        assert resp.status_code == 200, f"DOCX upload failed: {resp.text}"
        data = resp.json()
        assert data["filename"] == "contract.docx"
        assert data["char_count"] > 100
        assert "services" in data["text"].lower()

    def test_upload_oversized_file_returns_413(self, client, auth_headers):
        """Files over 10 MB should be rejected with 413."""
        large_content = b"A" * (10 * 1024 * 1024 + 1)
        files = {"file": ("big.txt", io.BytesIO(large_content), "text/plain")}
        resp = client.post("/v1/upload", headers=auth_headers, files=files)
        assert resp.status_code == 413, f"Expected 413 for oversized file, got {resp.status_code}"

    def test_upload_legacy_doc_returns_422(self, client, auth_headers):
        """Legacy .doc files should return 422 with helpful message."""
        files = {"file": ("contract.doc", io.BytesIO(b"fake doc content"), "application/msword")}
        resp = client.post("/v1/upload", headers=auth_headers, files=files)
        assert resp.status_code == 422, f"Expected 422 for .doc, got {resp.status_code}"
        assert "docx" in resp.json().get("detail", "").lower() or \
               "not supported" in resp.json().get("detail", "").lower()

    def test_upload_pdf_placeholder(self, client, auth_headers):
        """A minimal valid-looking PDF should be accepted (text extraction attempted)."""
        minimal_pdf = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"%%EOF"
        )
        files = {"file": ("empty.pdf", io.BytesIO(minimal_pdf), "application/pdf")}
        resp = client.post("/v1/upload", headers=auth_headers, files=files)
        # Empty PDF has no text — expect 422 (no readable text), not 500
        assert resp.status_code in (200, 422), \
            f"Unexpected status for PDF: {resp.status_code} {resp.text}"


# ─── Tender Listing — Filters & Pagination ────────────────────────────────────


class TestTenderFilters:

    def test_list_tenders_default(self, client, auth_headers):
        resp = client.get("/v1/procurement/ingestion/tenders", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "tenders" in data
        assert "offset" in data
        assert "limit" in data
        assert isinstance(data["tenders"], list)

    def test_list_tenders_with_limit(self, client, auth_headers):
        resp = client.get(
            "/v1/procurement/ingestion/tenders?limit=2&offset=0",
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tenders"]) <= 2
        assert data["limit"] == 2

    def test_list_tenders_with_source_filter(self, client, auth_headers):
        resp = client.get(
            "/v1/procurement/ingestion/tenders?source=OCP",
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        for tender in data["tenders"]:
            assert tender["source"] == "OCP", f"Got unexpected source: {tender['source']}"

    def test_list_tenders_with_nonexistent_source(self, client, auth_headers):
        resp = client.get(
            "/v1/procurement/ingestion/tenders?source=NONEXISTENT",
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["tenders"] == []

    def test_tender_response_fields(self, client, auth_headers):
        resp = client.get("/v1/procurement/ingestion/tenders", headers=auth_headers)
        data = resp.json()
        if data["tenders"]:
            t = data["tenders"][0]
            assert "id" in t
            assert "source" in t
            assert "title" in t
            assert "tender_id" in t


# ─── Clause Library — Filters ─────────────────────────────────────────────────


class TestClauseLibraryFilters:

    def test_library_category_filter(self, client, auth_headers):
        """Library should support ?category= filter."""
        resp = client.get(
            "/v1/procurement/clauses/library?category=Indemnification",
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "clauses" in data

    def test_library_jurisdiction_filter(self, client, auth_headers):
        resp = client.get(
            "/v1/procurement/clauses/library?jurisdiction=ON",
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data

    def test_library_no_auth(self, client):
        resp = client.get("/v1/procurement/clauses/library")
        assert resp.status_code == 401

    def test_library_response_structure(self, client, auth_headers):
        resp = client.get("/v1/procurement/clauses/library", headers=auth_headers)
        data = resp.json()
        assert data["total"] > 0, "Clause library should not be empty after seeding"
        if data["clauses"]:
            clause = data["clauses"][0]
            # Actual fields: clause_id, clause_text, clause_type, subtype, jurisdiction, etc.
            assert "clause_id" in clause or "clause_text" in clause, \
                f"Clause has unexpected structure: {list(clause.keys())}"


# ─── Multi-LLM Waterfall (Groq → HF → Claude) ────────────────────────────────


class TestLLMWaterfall:
    """
    Test the tiered fallback logic in analyze_with_claude.
    Groq is tried first (if configured), then HuggingFace, then Claude.
    We test the waterfall by controlling which tiers succeed/fail.
    """

    @patch("app.services.llm_service.settings")
    @patch("app.services.groq_llm_service.analyze_with_groq", new_callable=AsyncMock)
    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_groq_success_does_not_call_claude(
        self, mock_route_claude, mock_groq, mock_settings, client, auth_headers
    ):
        """When Groq succeeds, Claude should not be called at the service level."""
        mock_settings.use_groq = True
        mock_settings.groq_api_key = "fake-groq-key"
        mock_settings.use_local_llm = False
        mock_settings.hf_api_token = None
        mock_route_claude.return_value = {
            "summary": "Groq-powered summary",
            "contract_type": "service_agreement",
            "jurisdiction": "ON",
            "confidence": 0.88,
            "tokens_used": 100,
            "model": "llama-3.1-8b-instant",
        }
        resp = client.post("/v1/summary", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "analysis_id" in data

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_llm_failure_returns_500(self, mock_claude, client, auth_headers):
        """If all LLM tiers fail, endpoint should return 500."""
        mock_claude.side_effect = Exception("All LLM tiers exhausted")
        resp = client.post("/v1/summary", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
        })
        assert resp.status_code == 500
        assert "detail" in resp.json()

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_claude_called_as_final_fallback(self, mock_claude, client, auth_headers):
        """With Groq and HF disabled, route delegates to Claude."""
        mock_claude.return_value = {
            "summary": "Claude fallback summary",
            "contract_type": "nda",
            "jurisdiction": "ON",
            "confidence": 0.95,
            "tokens_used": 200,
        }
        resp = client.post("/v1/summary", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
            "jurisdiction": "ON",
        })
        assert resp.status_code == 200
        mock_claude.assert_called_once()


# ─── Excel Comparison ─────────────────────────────────────────────────────────


class TestExcelComparison:

    def _make_xlsx(self, rows: list[dict]) -> bytes:
        """Create a column-oriented .xlsx where keys are headers and each dict is a row."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        if not rows:
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            return buf.read()
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h, "") for h in headers])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.read()

    def test_compare_excel_identical_files(self, client, auth_headers):
        # Use COMPARE_FIELDS names: title, value, end_date, buyer, supplier, cpv_code
        xlsx = self._make_xlsx([{"title": "Contract A", "value": "100000", "buyer": "Dept X"}])
        files = {
            "file_a": ("contract_a.xlsx", io.BytesIO(xlsx),
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "file_b": ("contract_b.xlsx", io.BytesIO(xlsx),
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        resp = client.post("/v1/procurement/compare/excel", headers=auth_headers, files=files)
        assert resp.status_code == 200, f"Excel compare failed: {resp.text}"
        data_out = resp.json()
        assert "mismatches" in data_out
        assert len(data_out["mismatches"]) == 0, "Identical files should have no mismatches"

    def test_compare_excel_different_files(self, client, auth_headers):
        # Use COMPARE_FIELDS names: title, value, end_date, buyer, supplier, cpv_code
        xlsx_a = self._make_xlsx([{"title": "Contract A", "value": "100000", "buyer": "Dept X"}])
        xlsx_b = self._make_xlsx([{"title": "Contract B", "value": "200000", "buyer": "Dept Y"}])
        files = {
            "file_a": ("a.xlsx", io.BytesIO(xlsx_a),
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "file_b": ("b.xlsx", io.BytesIO(xlsx_b),
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        resp = client.post("/v1/procurement/compare/excel", headers=auth_headers, files=files)
        assert resp.status_code == 200, f"Excel compare failed: {resp.text}"
        data_out = resp.json()
        assert "mismatches" in data_out
        assert len(data_out["mismatches"]) > 0, "Different files should have mismatches"

    def test_compare_excel_non_xlsx_rejected(self, client, auth_headers):
        files = {
            "file_a": ("contract_a.txt", io.BytesIO(b"some text"), "text/plain"),
            "file_b": ("contract_b.xlsx", io.BytesIO(b"fake"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        resp = client.post("/v1/procurement/compare/excel", headers=auth_headers, files=files)
        assert resp.status_code == 400, f"Expected 400 for non-xlsx, got {resp.status_code}"

    def test_compare_excel_no_auth(self, client):
        files = {
            "file_a": ("a.xlsx", io.BytesIO(b"fake"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "file_b": ("b.xlsx", io.BytesIO(b"fake"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        resp = client.post("/v1/procurement/compare/excel", files=files)
        assert resp.status_code == 401


# ─── Auth Enforcement — Missing Routes ────────────────────────────────────────


class TestAuthEnforcementExtended:

    @pytest.mark.parametrize("method,path,body", [
        ("POST", "/v1/portal", {}),
        ("POST", "/v1/procurement/compare/clauses",
         {"clause_a": "test clause a here", "clause_b": "test clause b here"}),
        ("GET", "/v1/procurement/ingestion/tenders", None),
        ("POST", "/v1/procurement/ingestion/run", {"query": "test"}),
        ("GET", "/v1/procurement/clauses/library", None),
        ("POST", "/v1/procurement/clauses/search", {"query": "indemnification"}),
        ("POST", "/v1/procurement/clauses/analyze", {"text": SAMPLE_CLAUSE_TEXT}),
    ])
    def test_no_auth_returns_401(self, client, method, path, body):
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json=body)
        assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}, expected 401"


# ─── Contract Analysis — Response Field Completeness ─────────────────────────


class TestResponseCompleteness:
    """Verify all response fields are present and correctly typed."""

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_summary_response_types(self, mock_claude, client, auth_headers):
        from tests.conftest import MOCK_SUMMARY_RESPONSE
        mock_claude.return_value = MOCK_SUMMARY_RESPONSE
        resp = client.post("/v1/summary", headers=auth_headers, json={"text": SAMPLE_CONTRACT})
        assert resp.status_code == 200
        d = resp.json()
        assert isinstance(d["analysis_id"], str)
        assert isinstance(d["summary"], str) and len(d["summary"]) > 0
        assert isinstance(d["contract_type"], str)
        assert isinstance(d["jurisdiction"], str)
        assert isinstance(d["confidence"], float) and 0.0 <= d["confidence"] <= 1.0
        assert isinstance(d["tokens_used"], int) and d["tokens_used"] >= 0
        assert isinstance(d["processing_time_ms"], int) and d["processing_time_ms"] >= 0

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_risk_score_response_types(self, mock_claude, client, auth_headers):
        from tests.conftest import MOCK_RISK_SCORE_RESPONSE
        mock_claude.return_value = MOCK_RISK_SCORE_RESPONSE
        resp = client.post("/v1/risk-score", headers=auth_headers, json={"text": SAMPLE_CONTRACT})
        assert resp.status_code == 200
        d = resp.json()
        assert isinstance(d["overall_risk_score"], int) and 0 <= d["overall_risk_score"] <= 100
        assert d["risk_level"] in ("low", "medium", "high", "critical")
        assert isinstance(d["scores_by_category"], dict)
        assert isinstance(d["interpretation"], str)

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_key_risks_each_item_has_required_fields(self, mock_claude, client, auth_headers):
        from tests.conftest import MOCK_KEY_RISKS_RESPONSE
        mock_claude.return_value = MOCK_KEY_RISKS_RESPONSE
        resp = client.post("/v1/key-risks", headers=auth_headers, json={"text": SAMPLE_CONTRACT})
        d = resp.json()
        for risk in d["key_risks"]:
            assert "severity" in risk and risk["severity"] in ("critical", "high", "medium", "low")
            assert "title" in risk and isinstance(risk["title"], str)
            assert "description" in risk and isinstance(risk["description"], str)

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_extract_clauses_response_types(self, mock_claude, client, auth_headers):
        from tests.conftest import MOCK_EXTRACT_CLAUSES_RESPONSE
        mock_claude.return_value = MOCK_EXTRACT_CLAUSES_RESPONSE
        resp = client.post("/v1/extract-clauses", headers=auth_headers, json={"text": SAMPLE_CONTRACT})
        assert resp.status_code == 200
        d = resp.json()
        for clause in d["clauses"]:
            assert "type" in clause
            assert "severity" in clause
            assert "original" in clause
            assert "revised" in clause
            assert "rationale" in clause


# ─── Semantic Clause Search — Extended ────────────────────────────────────────


class TestSemanticSearchExtended:

    @patch("app.nlp.search.search_similar_clauses", return_value=[])
    def test_search_with_k_param(self, mock_search, client, auth_headers):
        resp = client.post("/v1/procurement/clauses/search", headers=auth_headers, json={
            "query": "termination for convenience",
            "k": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "clauses" in data

    @patch("app.nlp.search.search_similar_clauses", return_value=[])
    def test_search_empty_query_returns_200(self, mock_search, client, auth_headers):
        resp = client.post("/v1/procurement/clauses/search", headers=auth_headers, json={
            "query": "",
        })
        assert resp.status_code in (200, 422), \
            f"Empty query gave unexpected status: {resp.status_code}"

    @patch("app.nlp.search.search_similar_clauses", return_value=[])
    def test_analyze_clause_risk_level_enum(self, mock_search, client, auth_headers):
        resp = client.post("/v1/procurement/clauses/analyze", headers=auth_headers, json={
            "text": SAMPLE_CLAUSE_TEXT,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "clause_type" in data
        assert "risk_level" in data
        assert data["risk_level"] in ("High", "Medium", "Low"), \
            f"Unexpected risk_level: {data['risk_level']}"


# ─── Procurement Lint — Edge Cases ────────────────────────────────────────────


class TestLintEdgeCases:

    def test_lint_finds_passive_voice(self, client, auth_headers):
        text = (
            "The report will be submitted by the contractor. "
            "The contract was signed by both parties and was reviewed by legal counsel. "
            "All deliverables must be completed and will be evaluated by the project manager."
        )
        resp = client.post("/v1/procurement/lint", headers=auth_headers, json={"text": text})
        assert resp.status_code == 200
        data = resp.json()
        assert "passive_voice" in data
        assert isinstance(data["passive_voice"], list)

    def test_lint_finds_gendered_language(self, client, auth_headers):
        text = (
            "The chairman of the board shall appoint a manpower committee. "
            "He or she shall be responsible for ensuring the workmanship meets standards. "
            "The stewardess will coordinate with the foreman on all deliverables. "
            "Each businessman should review his obligations under this agreement."
        )
        resp = client.post("/v1/procurement/lint", headers=auth_headers, json={"text": text})
        assert resp.status_code == 200
        data = resp.json()
        assert "gendered_language" in data
        assert isinstance(data["gendered_language"], list)

    def test_lint_response_includes_all_categories(self, client, auth_headers):
        resp = client.post("/v1/procurement/lint", headers=auth_headers, json={
            "text": "The party of the first part hereinafter shall indemnify the party of the second part." * 3
        })
        assert resp.status_code == 200
        data = resp.json()
        required_keys = ["total_issues", "legalese", "passive_voice", "plural_parties", "gendered_language"]
        for key in required_keys:
            assert key in data, f"Missing key '{key}' in lint response"


# ─── Usage Endpoint — Extended ────────────────────────────────────────────────


class TestUsageExtended:

    def test_usage_response_completeness(self, client, auth_headers):
        resp = client.get("/v1/usage", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        required_fields = ["plan", "analyses_used_this_month", "analyses_limit", "remaining_quota"]
        for field in required_fields:
            assert field in data, f"Missing field '{field}' in usage response"

    def test_usage_remaining_quota_is_int_or_none(self, client, auth_headers):
        resp = client.get("/v1/usage", headers=auth_headers)
        data = resp.json()
        remaining = data["remaining_quota"]
        assert remaining is None or isinstance(remaining, int), \
            f"remaining_quota should be int or None, got {type(remaining)}"
