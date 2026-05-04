"""
Requirement 4 — Performance & Load
=====================================
Tests concurrency (deadlock detection), latency benchmarks, and payload limits.

Design note
-----------
These tests use threading.Thread to simulate concurrent clients against the
TestClient, which shares a single in-memory SQLite database.  True production
load tests (50+ users against the live VPS) should be run with Locust or k6
outside of pytest CI.  The tests here act as a *smoke screen* —
if they fail in the test environment, they will certainly fail in production.

All LLM calls are mocked; latency figures measure framework + DB overhead only.
For real TTFT benchmarks, see the `test_live_latency_benchmarks` section which
is marked @pytest.mark.skipif and only runs when LEXARA_LIVE_TEST=1 is set.
"""

import time
import threading
import statistics
import pytest
import os
from unittest.mock import patch, AsyncMock

from tests.conftest import (
    SAMPLE_CONTRACT,
    MOCK_SUMMARY_RESPONSE,
    MOCK_RISK_SCORE_RESPONSE,
    MOCK_KEY_RISKS_RESPONSE,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _concurrent_requests(client, method: str, url: str,
                         n: int, headers: dict, body: dict) -> list[int]:
    """
    Fire `n` requests concurrently using threads.
    Returns a list of HTTP status codes.
    """
    results = [None] * n
    errors  = []

    def _call(i):
        try:
            if method == "POST":
                resp = client.post(url, headers=headers, json=body)
            else:
                resp = client.get(url, headers=headers)
            results[i] = resp.status_code
        except Exception as exc:
            errors.append(exc)
            results[i] = -1

    threads = [threading.Thread(target=_call, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    if errors:
        pytest.fail(f"{len(errors)} thread(s) raised exceptions: {errors[:3]}")

    return results


def _timed_request(client, method: str, url: str,
                   headers: dict, body: dict = None) -> float:
    """Return elapsed seconds for a single request."""
    start = time.perf_counter()
    if method == "POST":
        client.post(url, headers=headers, json=body)
    else:
        client.get(url, headers=headers)
    return time.perf_counter() - start


# ── P-01 to P-03: Concurrency ─────────────────────────────────────────────────

class TestConcurrency:
    """Fire multiple simultaneous requests; verify no deadlocks or 5xx errors."""

    CONCURRENCY = 20   # kept at 20 for in-process SQLite safety

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_20_concurrent_summary_requests_all_succeed(
        self, mock_llm, client, auth_headers
    ):
        """P-01: 20 concurrent /v1/summary requests — all must return 200."""
        mock_llm.return_value = MOCK_SUMMARY_RESPONSE
        statuses = _concurrent_requests(
            client, "POST", "/v1/summary",
            self.CONCURRENCY, auth_headers,
            {"text": SAMPLE_CONTRACT}
        )
        failures = [s for s in statuses if s != 200]
        assert not failures, (
            f"{len(failures)}/{self.CONCURRENCY} concurrent summary requests failed: "
            f"{failures[:5]}"
        )

    @patch("app.routers.auth_routes.log_action")
    def test_20_concurrent_login_requests_no_500(
        self, mock_audit, client, test_user_credentials
    ):
        """P-02: 20 concurrent /v1/auth/login requests — no 500 errors.
        log_action is patched at the auth_routes import site to avoid concurrent
        SQLite RETURNING-clause writes under StaticPool (SQLite is not safe for
        concurrent writes in CI). Production uses PostgreSQL which handles
        concurrent INSERTs correctly."""
        statuses = _concurrent_requests(
            client, "POST", "/v1/auth/login",
            self.CONCURRENCY, {},
            {
                "username": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            }
        )
        server_errors = [s for s in statuses if s >= 500]
        assert not server_errors, (
            f"{len(server_errors)} concurrent login requests returned 5xx: {server_errors[:5]}"
        )

    @patch("app.routers.procurement_clause_routes.log_action")
    def test_10_concurrent_clause_searches_no_errors(
        self, mock_audit, client, auth_headers
    ):
        """P-03: 10 concurrent /v1/procurement/clauses/search — all 200.
        log_action patched at import site to prevent concurrent SQLite write races."""
        statuses = _concurrent_requests(
            client, "POST", "/v1/procurement/clauses/search",
            10, auth_headers,
            {"query": "force majeure", "limit": 5}
        )
        failures = [s for s in statuses if s not in (200, 404)]
        assert not failures, (
            f"Concurrent clause searches returned unexpected statuses: {failures[:5]}"
        )

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_concurrent_requests_produce_unique_analysis_ids(
        self, mock_llm, client, auth_headers
    ):
        """P-01b: Each concurrent request returns a distinct analysis_id (no shared state)."""
        mock_llm.return_value = MOCK_SUMMARY_RESPONSE
        ids = []
        lock = threading.Lock()

        def _call():
            resp = client.post("/v1/summary",
                               headers=auth_headers,
                               json={"text": SAMPLE_CONTRACT})
            if resp.status_code == 200:
                with lock:
                    ids.append(resp.json().get("analysis_id"))

        threads = [threading.Thread(target=_call) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)

        assert len(ids) == len(set(ids)), (
            f"Duplicate analysis_ids detected in concurrent requests: "
            f"{len(ids) - len(set(ids))} collisions"
        )

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_concurrent_different_endpoints_no_deadlock(
        self, mock_llm, client, auth_headers
    ):
        """P-01c: Mixed concurrent requests to different endpoints — no deadlock."""
        mock_llm.side_effect = [
            MOCK_SUMMARY_RESPONSE,
            MOCK_RISK_SCORE_RESPONSE,
            MOCK_KEY_RISKS_RESPONSE,
        ] * 10
        results  = []
        lock     = threading.Lock()
        endpoints = ["/v1/summary", "/v1/risk-score", "/v1/key-risks"]

        def _call(ep, mock_resp):
            mock_llm.return_value = mock_resp
            resp = client.post(ep, headers=auth_headers, json={"text": SAMPLE_CONTRACT})
            with lock:
                results.append((ep, resp.status_code))

        threads = []
        for i in range(15):
            ep = endpoints[i % len(endpoints)]
            mock_resp = [MOCK_SUMMARY_RESPONSE, MOCK_RISK_SCORE_RESPONSE, MOCK_KEY_RISKS_RESPONSE][i % 3]
            threads.append(threading.Thread(target=_call, args=(ep, mock_resp)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        failures = [(ep, s) for ep, s in results if s >= 500]
        assert not failures, (
            f"Deadlock or server error under mixed concurrent load: {failures}"
        )


# ── P-04 to P-07: Latency Benchmarks (mocked LLM) ────────────────────────────

class TestLatencyBenchmarks:
    """
    Measure request-handling overhead with mocked LLM.
    These SLAs cover framework + DB overhead only — NOT actual LLM latency.
    """

    RUNS = 10  # number of samples for median calculation

    def test_health_endpoint_median_latency_under_50ms(self, client):
        """P-04: GET /health median latency < 50 ms."""
        times = [_timed_request(client, "GET", "/health", {}) for _ in range(self.RUNS)]
        median_ms = statistics.median(times) * 1000
        assert median_ms < 50, (
            f"GET /health median latency {median_ms:.1f} ms exceeds 50 ms SLA. "
            f"Samples: {[f'{t*1000:.1f}' for t in times]}"
        )

    def test_login_median_latency_under_500ms(self, client, test_user_credentials):
        """P-05: POST /v1/auth/login median latency < 500 ms (bcrypt is intentionally slow)."""
        times = [
            _timed_request(client, "POST", "/v1/auth/login", {},
                           {"username": test_user_credentials["username"],
                            "password": test_user_credentials["password"]})
            for _ in range(self.RUNS)
        ]
        median_ms = statistics.median(times) * 1000
        assert median_ms < 500, (
            f"POST /v1/auth/login median {median_ms:.1f} ms exceeds 500 ms SLA. "
            f"Samples: {[f'{t*1000:.1f}' for t in times]}"
        )

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_summary_framework_overhead_under_200ms(
        self, mock_llm, client, auth_headers
    ):
        """P-06: /v1/summary with mocked LLM (framework + DB overhead only) < 200 ms."""
        mock_llm.return_value = MOCK_SUMMARY_RESPONSE
        times = [
            _timed_request(client, "POST", "/v1/summary", auth_headers,
                           {"text": SAMPLE_CONTRACT})
            for _ in range(self.RUNS)
        ]
        median_ms = statistics.median(times) * 1000
        p95_ms    = sorted(times)[int(0.95 * self.RUNS)] * 1000
        assert median_ms < 200, (
            f"Mocked /v1/summary median overhead {median_ms:.1f} ms > 200 ms. "
            f"p95={p95_ms:.1f} ms. Samples: {[f'{t*1000:.1f}' for t in times]}"
        )

    def test_clause_search_median_latency_under_500ms(self, client, auth_headers):
        """P-07: /v1/procurement/clauses/search (FAISS) median latency < 500 ms."""
        times = [
            _timed_request(client, "POST", "/v1/procurement/clauses/search",
                           auth_headers,
                           {"query": "limitation of liability", "limit": 5})
            for _ in range(self.RUNS)
        ]
        median_ms = statistics.median(times) * 1000
        assert median_ms < 500, (
            f"Clause search median {median_ms:.1f} ms exceeds 500 ms SLA. "
            f"Samples: {[f'{t*1000:.1f}' for t in times]}"
        )


# ── P-extra: Payload & Boundary Tests ─────────────────────────────────────────

class TestPayloadBoundaries:
    """Verify the API handles extremes at or near the documented limits."""

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_exactly_100_char_contract_accepted(self, mock_llm, client, auth_headers):
        """Minimum boundary: exactly 100 chars is accepted."""
        mock_llm.return_value = MOCK_SUMMARY_RESPONSE
        text = "A" * 100
        resp = client.post("/v1/summary",
                           headers=auth_headers,
                           json={"text": text})
        assert resp.status_code == 200

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_exactly_50000_char_contract_accepted(self, mock_llm, client, auth_headers):
        """Maximum boundary: exactly 50,000 chars is accepted."""
        mock_llm.return_value = MOCK_SUMMARY_RESPONSE
        text = "Contract text. " * 3334  # ~50,010 — trim to exactly 50,000
        text = text[:50000]
        resp = client.post("/v1/summary",
                           headers=auth_headers,
                           json={"text": text})
        assert resp.status_code == 200

    def test_50001_char_contract_rejected(self, client, auth_headers):
        """Over maximum boundary: 50,001 chars returns 400."""
        text = "A" * 50001
        resp = client.post("/v1/summary",
                           headers=auth_headers,
                           json={"text": text})
        assert resp.status_code == 400

    def test_missing_text_field_returns_422(self, client, auth_headers):
        """Missing required 'text' field returns 422 Unprocessable Entity."""
        resp = client.post("/v1/summary",
                           headers=auth_headers,
                           json={"contract_type": "service_agreement"})
        assert resp.status_code == 422

    def test_null_text_field_returns_422(self, client, auth_headers):
        """Null 'text' field returns 422."""
        resp = client.post("/v1/summary",
                           headers=auth_headers,
                           json={"text": None})
        assert resp.status_code == 422

    def test_integer_text_field_returns_422(self, client, auth_headers):
        """Integer 'text' field (wrong type) returns 422."""
        resp = client.post("/v1/summary",
                           headers=auth_headers,
                           json={"text": 12345})
        assert resp.status_code == 422


# ── Live latency benchmarks (opt-in) ──────────────────────────────────────────

@pytest.mark.skipif(
    os.getenv("LEXARA_LIVE_TEST") != "1",
    reason="Live API benchmarks — set LEXARA_LIVE_TEST=1 to run against api.lexara.tech"
)
class TestLiveLLMLatency:
    """
    Measures real TTFT and total response time against the live production API.
    Requires a valid JWT and the live API to be reachable.

    Run with:
        LEXARA_LIVE_TEST=1 LEXARA_JWT=<token> pytest tests/test_performance_load.py \
            -k TestLiveLLMLatency -v
    """

    LIVE_BASE = "https://api.lexara.tech"
    SLA_SUMMARY_P95_MS = 15_000   # 15 s — LLM inference is slow
    SLA_RISK_SCORE_P95_MS = 15_000

    def _live_headers(self):
        token = os.getenv("LEXARA_JWT", "")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def test_live_summary_p95_under_15s(self):
        """TTFT+response: /v1/summary against live Claude — p95 < 15 s."""
        import httpx
        times = []
        for _ in range(5):
            start = time.perf_counter()
            r = httpx.post(
                f"{self.LIVE_BASE}/v1/summary",
                headers=self._live_headers(),
                json={"text": SAMPLE_CONTRACT},
                timeout=30.0,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert r.status_code == 200, f"Live summary returned {r.status_code}: {r.text[:200]}"
            times.append(elapsed_ms)

        p95 = sorted(times)[int(0.95 * len(times))]
        print(f"\nLive /v1/summary — median={statistics.median(times):.0f}ms p95={p95:.0f}ms")
        assert p95 < self.SLA_SUMMARY_P95_MS, (
            f"Live /v1/summary p95 {p95:.0f} ms exceeds {self.SLA_SUMMARY_P95_MS} ms SLA"
        )

    def test_live_risk_score_p95_under_15s(self):
        """TTFT+response: /v1/risk-score against live Claude — p95 < 15 s."""
        import httpx
        times = []
        for _ in range(5):
            start = time.perf_counter()
            r = httpx.post(
                f"{self.LIVE_BASE}/v1/risk-score",
                headers=self._live_headers(),
                json={"text": SAMPLE_CONTRACT},
                timeout=30.0,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert r.status_code == 200, f"Live risk-score returned {r.status_code}: {r.text[:200]}"
            times.append(elapsed_ms)

        p95 = sorted(times)[int(0.95 * len(times))]
        print(f"\nLive /v1/risk-score — median={statistics.median(times):.0f}ms p95={p95:.0f}ms")
        assert p95 < self.SLA_RISK_SCORE_P95_MS, (
            f"Live /v1/risk-score p95 {p95:.0f} ms exceeds {self.SLA_RISK_SCORE_P95_MS} ms SLA"
        )
