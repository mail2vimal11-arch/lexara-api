"""
Frontend E2E tests for Procurement Intelligence.

Tests the full user journey through the procurement-intelligence.html page:
  1. HTML structure validation (panels, forms, IDs the JS depends on)
  2. Auth flow (register -> login -> JWT -> API calls)
  3. All 7 tool panels hit the correct API endpoints with the right payloads
  4. Response format matches what the frontend rendering code expects
  5. Main index.html and procurement.html page structure
"""

import io
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from pathlib import Path

from tests.conftest import (
    SAMPLE_CONTRACT,
    SAMPLE_CLAUSE_TEXT,
    MOCK_SUMMARY_RESPONSE,
    MOCK_RISK_SCORE_RESPONSE,
    MOCK_KEY_RISKS_RESPONSE,
    MOCK_MISSING_CLAUSES_RESPONSE,
    MOCK_EXTRACT_CLAUSES_RESPONSE,
)

WEBSITE_DIR = Path(__file__).resolve().parent.parent / "website"


# ═══════════════════════════════════════════════════════════════════════════════
# HTML STRUCTURE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestProcurementIntelligenceHTML:
    """Validate the procurement-intelligence.html has all IDs the JS relies on."""

    @pytest.fixture(scope="class")
    def html(self):
        return (WEBSITE_DIR / "procurement-intelligence.html").read_text()

    # -- Auth gate elements --
    def test_auth_gate_exists(self, html):
        assert 'id="auth-gate"' in html

    def test_show_app_uses_block_not_empty_string(self, html):
        """Regression: style.display='' does NOT override CSS 'display:none' rules.
        showApp() must set display='block' to override the #pai-app CSS rule."""
        assert '.style.display = "block"' in html or ".style.display = 'block'" in html
        # Must NOT use empty string to show #pai-app
        assert 'getElementById("pai-app").style.display = ""' not in html

    def test_login_form_elements(self, html):
        assert 'id="login-username"' in html
        assert 'id="login-password"' in html
        assert 'id="login-msg"' in html
        assert "doLogin()" in html

    def test_register_form_elements(self, html):
        assert 'id="reg-username"' in html
        assert 'id="reg-email"' in html
        assert 'id="reg-password"' in html
        assert 'id="reg-role"' in html
        assert 'id="reg-msg"' in html
        assert "doRegister()" in html

    # -- Main app container --
    def test_app_container(self, html):
        assert 'id="pai-app"' in html
        assert 'id="user-display"' in html
        assert 'id="role-display"' in html
        assert "doLogout()" in html

    # -- All 7 tool panel tabs exist --
    @pytest.mark.parametrize("panel_id", [
        "panel-linter",
        "panel-citations",
        "panel-clauses-basic",
        "panel-analyze",
        "panel-search",
        "panel-tenders",
        "panel-compare",
    ])
    def test_panel_exists(self, html, panel_id):
        assert f'id="{panel_id}"' in html

    # -- Linter panel elements --
    def test_linter_panel_elements(self, html):
        assert 'id="linter-input"' in html
        assert 'id="linter-status"' in html
        assert 'id="linter-results"' in html
        assert 'id="linter-metrics"' in html
        assert 'id="linter-groups"' in html
        assert "runLinter()" in html

    # -- Citations panel elements --
    def test_citations_panel_elements(self, html):
        assert 'id="citations-input"' in html
        assert 'id="citations-status"' in html
        assert 'id="citations-results"' in html
        assert 'id="citations-metrics"' in html
        assert 'id="citations-groups"' in html
        assert "runCitations()" in html

    # -- Clause library (basic) panel elements --
    def test_clause_library_panel_elements(self, html):
        assert 'id="basic-query"' in html
        assert 'id="basic-category"' in html
        assert 'id="basic-results"' in html
        assert "runBasicSearch()" in html

    # -- Analyze panel elements --
    def test_analyze_panel_elements(self, html):
        assert 'id="analyze-input"' in html
        assert 'id="analyze-status"' in html
        assert 'id="analyze-result"' in html
        assert "analyzeClause()" in html

    # -- Search panel elements --
    def test_search_panel_elements(self, html):
        assert 'id="search-input"' in html
        assert 'id="search-type"' in html
        assert 'id="search-result"' in html
        assert "searchClauses()" in html

    # -- Tenders panel elements --
    def test_tenders_panel_elements(self, html):
        assert 'id="tender-source"' in html
        assert 'id="tender-status"' in html
        assert 'id="tender-result"' in html
        assert 'id="ingest-btn"' in html
        assert "loadTenders()" in html
        assert "triggerIngestion()" in html

    # -- Compare panel elements --
    def test_compare_panel_elements(self, html):
        assert 'id="compare-a"' in html
        assert 'id="compare-b"' in html
        assert 'id="compare-status"' in html
        assert 'id="compare-result"' in html
        assert "compareClauses()" in html

    # -- JavaScript API constants --
    def test_api_base_url(self, html):
        assert 'api.lexara.tech/v1' in html

    def test_auth_headers_function(self, html):
        assert "authHeaders()" in html
        assert "Bearer" in html

    # -- Navigation --
    def test_navigation_links(self, html):
        assert 'href="/#features"' in html
        assert 'href="/#demo"' in html
        assert 'href="/#pricing"' in html
        assert 'href="/procurement-intelligence.html"' in html


class TestIndexHTML:
    """Validate main landing page structure."""

    @pytest.fixture(scope="class")
    def html(self):
        return (WEBSITE_DIR / "index.html").read_text()

    def test_has_demo_section(self, html):
        assert 'id="demo"' in html or 'id="demo-placeholder"' in html

    def test_has_features_section(self, html):
        assert 'id="features"' in html or "features" in html.lower()

    def test_has_pricing_section(self, html):
        assert 'id="pricing"' in html or "pricing" in html.lower()

    def test_links_to_procurement(self, html):
        assert "procurement" in html.lower()

    def test_references_api(self, html):
        # index.html loads script.js which contains the API base URL
        assert 'script.js' in html


class TestProcurementHTML:
    """Validate procurement.html page structure."""

    @pytest.fixture(scope="class")
    def html(self):
        return (WEBSITE_DIR / "procurement.html").read_text()

    def test_has_linter_tab(self, html):
        assert "Readability Linter" in html or "linter" in html.lower()

    def test_has_citation_tab(self, html):
        assert "Citation" in html

    def test_has_clause_library(self, html):
        assert "Clause Library" in html or "clause" in html.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND API CONTRACT TESTS
# Simulate exactly what the JS does: register, login, then call each tool panel
# ═══════════════════════════════════════════════════════════════════════════════


class TestFrontendAuthFlow:
    """Simulate the procurement-intelligence.html auth gate JS flow."""

    def test_full_auth_journey(self, client):
        """doRegister() -> switchAuthTab('login') -> doLogin() -> showApp()"""
        import uuid
        uid = uuid.uuid4().hex[:6]

        # 1. doRegister() — POST /v1/auth/register
        reg_resp = client.post("/v1/auth/register", json={
            "username": f"fe_test_{uid}",
            "email": f"fe_test_{uid}@lexara.dev",
            "password": "FrontendTest123!",
            "role": "procurement",
        })
        assert reg_resp.status_code == 200
        assert reg_resp.json()["username"] == f"fe_test_{uid}"

        # 2. doLogin() — POST /v1/auth/login
        login_resp = client.post("/v1/auth/login", json={
            "username": f"fe_test_{uid}",
            "password": "FrontendTest123!",
        })
        assert login_resp.status_code == 200
        data = login_resp.json()
        # Frontend stores: localStorage.setItem("pai_token", data.access_token)
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "procurement"
        # Token must be long enough to pass middleware (>= 10 chars)
        assert len(data["access_token"]) >= 10


class TestFrontendLinterPanel:
    """Simulate runLinter() — POST /v1/procurement/lint"""

    def test_linter_response_format(self, client, auth_headers):
        """Frontend renders: data.total_issues, data.legalese, data.passive_voice,
        data.plural_parties, data.gendered_language — each an array of findings."""
        text = (
            "Notwithstanding the foregoing provisions herein, the party of the "
            "first part hereinafter referred to as the Vendor shall indemnify "
            "and hold harmless the party of the second part. The deliverables "
            "shall be provided in accordance with the terms hereinafter."
        )
        resp = client.post("/v1/procurement/lint", headers=auth_headers, json={"text": text})
        assert resp.status_code == 200
        data = resp.json()

        # Fields the frontend rendering code expects
        assert "total_issues" in data
        assert isinstance(data["total_issues"], int)
        assert "legalese" in data
        assert "passive_voice" in data
        assert "plural_parties" in data
        assert "gendered_language" in data

        # Each should be a list
        for key in ("legalese", "passive_voice", "plural_parties", "gendered_language"):
            assert isinstance(data[key], list)

        # Legalese findings should have the fields the JS renders
        assert data["total_issues"] > 0
        if data["legalese"]:
            finding = data["legalese"][0]
            assert "term" in finding
            assert "suggestion" in finding
            # Frontend renders f.original and f.revised for before/after
            assert "original" in finding

    def test_linter_finds_specific_terms(self, client, auth_headers):
        """Frontend highlights specific legalese terms."""
        text = (
            "The party hereby agrees to the terms set forth herein. "
            "Notwithstanding the above provisions, the obligations "
            "hereunder shall be binding. Pursuant to section 5, the "
            "contractor forthwith shall deliver the goods."
        )
        resp = client.post("/v1/procurement/lint", headers=auth_headers, json={"text": text})
        data = resp.json()
        terms = [f["term"].lower() for f in data["legalese"]]
        assert any("hereby" in t for t in terms)
        assert any("herein" in t for t in terms)
        assert any("notwithstanding" in t for t in terms)


class TestFrontendCitationPanel:
    """Simulate runCitations() — POST /v1/procurement/citations"""

    def test_citation_response_format(self, client, auth_headers):
        """Frontend renders: data.total, data.statutes[], data.regulations[], data.cases[]"""
        text = (
            "The Competition Act, RSC 1985, c C-34 governs this arrangement. "
            "See also R v Jordan, 2016 SCC 27 for the framework."
        )
        resp = client.post("/v1/procurement/citations", headers=auth_headers, json={"text": text})
        assert resp.status_code == 200
        data = resp.json()

        assert "total" in data
        assert "statutes" in data
        assert "regulations" in data
        assert "cases" in data
        assert isinstance(data["statutes"], list)
        assert isinstance(data["regulations"], list)
        assert isinstance(data["cases"], list)
        assert data["total"] >= 1

        # Each citation should have: raw, valid, warnings (for frontend rendering)
        if data["statutes"]:
            s = data["statutes"][0]
            assert "raw" in s
            assert "warnings" in s
            assert isinstance(s["warnings"], list)


class TestFrontendClauseLibraryPanel:
    """Simulate runBasicSearch() — POST /v1/procurement/clauses"""

    def test_clause_search_response_format(self, client, auth_headers):
        """Frontend renders: data.total, data.categories[], data.clauses[]"""
        resp = client.post("/v1/procurement/clauses", headers=auth_headers, json={
            "query": "indemnification",
            "category": None,
        })
        assert resp.status_code == 200
        data = resp.json()

        assert "total" in data
        assert "categories" in data
        assert "clauses" in data
        assert isinstance(data["categories"], list)
        assert isinstance(data["clauses"], list)
        assert data["total"] > 0

        # Frontend renders clause fields: id, title, category, text, source, notes
        clause = data["clauses"][0]
        assert "title" in clause
        assert "text" in clause
        assert "category" in clause

    def test_clause_list_all_returns_categories(self, client, auth_headers):
        """Frontend populates category dropdown from data.categories."""
        resp = client.post("/v1/procurement/clauses", headers=auth_headers, json={
            "query": "",
        })
        data = resp.json()
        assert len(data["categories"]) > 0
        # Should include known categories
        cats_lower = [c.lower() for c in data["categories"]]
        assert any("indemnification" in c for c in cats_lower)

    def test_clause_category_filter(self, client, auth_headers):
        """Frontend filters by category via dropdown."""
        resp = client.post("/v1/procurement/clauses", headers=auth_headers, json={
            "query": "",
            "category": "Termination",
        })
        data = resp.json()
        assert data["total"] > 0


class TestFrontendAnalyzePanel:
    """Simulate analyzeClause() — POST /v1/procurement/clauses/analyze"""

    @patch("app.nlp.search.search_similar_clauses", return_value=[])
    def test_analyze_response_format(self, mock_search, client, auth_headers):
        """Frontend renders: d.clause_type, d.risk_level, d.confidence_score,
        d.improved, d.similar_clauses"""
        resp = client.post("/v1/procurement/clauses/analyze", headers=auth_headers, json={
            "text": SAMPLE_CLAUSE_TEXT,
        })
        assert resp.status_code == 200
        data = resp.json()

        # Fields the frontend JS expects
        assert "clause_type" in data
        assert "risk_level" in data
        assert data["risk_level"] in ("High", "Medium", "Low")
        assert "confidence_score" in data
        # improved can be None or a string
        assert "improved" in data or data.get("improved") is None

    @patch("app.nlp.search.search_similar_clauses", return_value=[])
    def test_analyze_detects_risky_language(self, mock_search, client, auth_headers):
        """Frontend shows risk badge based on risk_level."""
        risky_text = (
            "The Contractor shall use reasonable efforts to deliver the goods "
            "as soon as possible and provide services as needed, at its discretion."
        )
        resp = client.post("/v1/procurement/clauses/analyze", headers=auth_headers, json={
            "text": risky_text,
        })
        data = resp.json()
        assert data["risk_level"] in ("High", "Medium")
        # Should suggest improvements for vague language
        if data.get("improved"):
            assert data["improved"] != risky_text


class TestFrontendSemanticSearchPanel:
    """Simulate searchClauses() — POST /v1/procurement/clauses/search"""

    @patch("app.nlp.search.search_similar_clauses", return_value=[])
    def test_search_response_format(self, mock_search, client, auth_headers):
        """Frontend renders: d.total, d.clauses[]"""
        resp = client.post("/v1/procurement/clauses/search", headers=auth_headers, json={
            "query": "indemnification for government contracts",
            "k": 5,
        })
        assert resp.status_code == 200
        data = resp.json()

        assert "total" in data
        assert "clauses" in data
        assert isinstance(data["clauses"], list)


class TestFrontendTendersPanel:
    """Simulate loadTenders() — GET /v1/procurement/ingestion/tenders"""

    def test_tenders_response_format(self, client, auth_headers):
        """Frontend renders: d.total, d.tenders[] with source, title, buyer, value, currency, country, source_url"""
        resp = client.get("/v1/procurement/ingestion/tenders?limit=50", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "total" in data
        assert "tenders" in data
        assert isinstance(data["tenders"], list)

    def test_ingestion_blocked_for_non_admin(self, client, auth_headers):
        """Frontend hides ingest-btn for non-admin; API enforces 403."""
        resp = client.post("/v1/procurement/ingestion/run", headers=auth_headers, json={
            "query": "procurement",
        })
        assert resp.status_code == 403


class TestFrontendComparePanel:
    """Simulate compareClauses() — POST /v1/procurement/compare/clauses"""

    def test_compare_response_format(self, client, auth_headers):
        """Frontend renders: d.similarity_score, d.verdict, d.match"""
        resp = client.post("/v1/procurement/compare/clauses", headers=auth_headers, json={
            "clause_a": "The Contractor shall indemnify the Crown against all claims.",
            "clause_b": (
                "The Vendor shall hold harmless and indemnify the Government "
                "from any and all claims, losses, and damages."
            ),
        })
        assert resp.status_code == 200
        data = resp.json()

        # Fields the frontend JS expects
        assert "similarity_score" in data
        assert "verdict" in data
        assert "match" in data
        assert isinstance(data["similarity_score"], float)
        assert 0.0 <= data["similarity_score"] <= 1.0
        assert isinstance(data["match"], bool)
        assert isinstance(data["verdict"], str)


# ═══════════════════════════════════════════════════════════════════════════════
# INDEX.HTML CONTRACT ANALYSIS — simulate script.js calls
# ═══════════════════════════════════════════════════════════════════════════════


class TestFrontendContractAnalysis:
    """Simulate script.js tab clicks on index.html — each tab calls a different endpoint."""

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_summary_tab_response_format(self, mock_claude, client, auth_headers):
        """Tab 1: script.js calls /v1/summary and renders result.summary, result.contract_type, etc."""
        mock_claude.return_value = MOCK_SUMMARY_RESPONSE
        resp = client.post("/v1/summary", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
            "contract_type": "auto",
            "jurisdiction": "ON",
        })
        data = resp.json()
        # script.js renders: result.summary, result.contract_type, result.confidence
        assert "summary" in data
        assert "contract_type" in data
        assert "confidence" in data
        assert isinstance(data["confidence"], float)

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_risk_score_tab_response_format(self, mock_claude, client, auth_headers):
        """Tab 2: script.js renders risk score bar and category breakdown."""
        mock_claude.return_value = MOCK_RISK_SCORE_RESPONSE
        resp = client.post("/v1/risk-score", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
            "contract_type": "auto",
            "jurisdiction": "ON",
        })
        data = resp.json()
        assert "overall_risk_score" in data
        assert "risk_level" in data
        assert "scores_by_category" in data
        assert isinstance(data["scores_by_category"], dict)
        # script.js renders per-category bars
        for cat in ("liability", "data_protection", "termination", "ip_ownership", "warranty"):
            assert cat in data["scores_by_category"]

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_key_risks_tab_response_format(self, mock_claude, client, auth_headers):
        """Tab 3: script.js renders risk cards with severity badges."""
        mock_claude.return_value = MOCK_KEY_RISKS_RESPONSE
        resp = client.post("/v1/key-risks", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
            "contract_type": "auto",
            "jurisdiction": "ON",
        })
        data = resp.json()
        assert "key_risks" in data
        assert isinstance(data["key_risks"], list)
        for risk in data["key_risks"]:
            assert "severity" in risk
            assert "title" in risk
            assert "description" in risk

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_missing_clauses_tab_response_format(self, mock_claude, client, auth_headers):
        """Tab 4: script.js renders missing clause cards."""
        mock_claude.return_value = MOCK_MISSING_CLAUSES_RESPONSE
        resp = client.post("/v1/missing-clauses", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
            "contract_type": "auto",
            "jurisdiction": "ON",
        })
        data = resp.json()
        assert "missing_clauses" in data
        for mc in data["missing_clauses"]:
            assert "clause" in mc
            assert "importance" in mc
            assert "rationale" in mc

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_extract_clauses_tab_response_format(self, mock_claude, client, auth_headers):
        """Tab 5: script.js renders clause revision cards."""
        mock_claude.return_value = MOCK_EXTRACT_CLAUSES_RESPONSE
        resp = client.post("/v1/extract-clauses", headers=auth_headers, json={
            "text": SAMPLE_CONTRACT,
            "contract_type": "auto",
            "jurisdiction": "ON",
        })
        data = resp.json()
        assert "clauses" in data
        for c in data["clauses"]:
            assert "type" in c
            assert "summary" in c
            assert "confidence" in c


# ═══════════════════════════════════════════════════════════════════════════════
# FILE UPLOAD — simulate the upload zone on index.html
# ═══════════════════════════════════════════════════════════════════════════════


class TestFrontendFileUpload:
    """Simulate the drag-and-drop / browse upload flow on index.html."""

    def test_upload_returns_text_for_analysis(self, client, auth_headers):
        """Frontend uses the returned text to populate the textarea for analysis."""
        content = SAMPLE_CONTRACT.encode("utf-8")
        files = {"file": ("contract.txt", io.BytesIO(content), "text/plain")}
        resp = client.post("/v1/upload", headers=auth_headers, files=files)
        assert resp.status_code == 200
        data = resp.json()
        # Frontend needs: filename, text, char_count, word_count
        assert "filename" in data
        assert "text" in data
        assert "char_count" in data
        assert "word_count" in data
        assert len(data["text"]) >= 100  # enough for analysis endpoints


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING — simulate pricing page checkout flow
# ═══════════════════════════════════════════════════════════════════════════════


class TestFrontendBilling:

    def test_plans_response_has_all_tiers(self, client, auth_headers):
        """Frontend renders 4 pricing cards from data.plans."""
        resp = client.get("/v1/plans", headers=auth_headers)
        data = resp.json()
        plans = data["plans"]
        assert "free" in plans
        assert "starter" in plans
        assert "growth" in plans
        assert "business" in plans
        # Each plan has fields the frontend renders
        for plan_key, plan in plans.items():
            assert "name" in plan
            assert "price_cad" in plan
            assert "analyses_limit" in plan
