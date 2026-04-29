"""
Tests for the N-bid competitive scenario stress-tester.

Covers both the service layer (simulate_bid_comparison) and the
/v1/bid-comparison/stress-test HTTP endpoint.

The router is not yet wired in app/main.py (the operator does that step
manually); tests register it dynamically before exercising the endpoint.
"""

import asyncio

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.routers import bid_comparison_routes
from app.services import scenario_simulator


# ---------------------------------------------------------------------------
# Wire the router for tests (idempotent)
# ---------------------------------------------------------------------------

_ROUTE_PATH = "/v1/bid-comparison/stress-test"


def _ensure_router_registered() -> None:
    paths = {getattr(r, "path", None) for r in app.router.routes}
    if _ROUTE_PATH not in paths:
        app.include_router(bid_comparison_routes.router)


_ensure_router_registered()


# ---------------------------------------------------------------------------
# Auto-stub the LLM-backed prevention summary so tests run offline & fast.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _stub_prevention_summary(monkeypatch):
    async def _fake_summary(**kwargs):
        clause_data = kwargs.get("clause_data") or {}
        scenario_type = kwargs.get("scenario_type", "scenario")
        return (
            f"[stub] {scenario_type} on "
            f"{clause_data.get('clause_key', 'clause')} prevention summary."
        )

    monkeypatch.setattr(
        scenario_simulator, "_generate_prevention_summary", _fake_summary
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _liability_clause(key: str, severity: str = "medium") -> dict:
    return {
        "clause_key": key,
        "clause_type": "liability",
        "risk_severity": severity,
        "original_text": "Aggregate liability capped at fees paid in prior 12 months.",
        "your_proposed_text": None,
    }


def _ip_clause(key: str, severity: str = "high") -> dict:
    return {
        "clause_key": key,
        "clause_type": "ip_ownership",
        "risk_severity": severity,
        "original_text": "Vendor retains all IP.",
        "your_proposed_text": None,
    }


def _termination_clause(key: str, severity: str = "medium") -> dict:
    return {
        "clause_key": key,
        "clause_type": "termination",
        "risk_severity": severity,
        "original_text": "Termination for cause on 30 days notice.",
        "your_proposed_text": None,
    }


def _session(value: float = 1_000_000.0) -> dict:
    return {"contract_value_cad": value, "jurisdiction_code": "ON"}


# ---------------------------------------------------------------------------
# Service-layer tests (deterministic math, run via asyncio.run)
# ---------------------------------------------------------------------------


def test_two_bid_comparison_lower_severity_ranks_better():
    """Same clause, lower risk_severity should rank ahead (lower weighted exposure)."""
    bid_safe = {
        "bid_id": "bid-safe",
        "vendor_name": "SafeVendor",
        "clauses": [_liability_clause("liab", severity="low")],
        "contract_value_cad": 1_000_000.0,
    }
    bid_risky = {
        "bid_id": "bid-risky",
        "vendor_name": "RiskyVendor",
        "clauses": [_liability_clause("liab", severity="critical")],
        "contract_value_cad": 1_000_000.0,
    }

    result = asyncio.run(
        scenario_simulator.simulate_bid_comparison(
            bids=[bid_safe, bid_risky],
            session_data=_session(),
        )
    )

    assert "bids" in result and len(result["bids"]) == 2
    ranking = {r["bid_id"]: r["rank"] for r in result["ranking"]}
    assert ranking["bid-safe"] == 1
    assert ranking["bid-risky"] == 2

    safe_w = next(b for b in result["bids"] if b["bid_id"] == "bid-safe")
    risky_w = next(b for b in result["bids"] if b["bid_id"] == "bid-risky")
    assert (
        risky_w["totals"]["weighted_exposure_cad"]
        > safe_w["totals"]["weighted_exposure_cad"]
    )

    # head-to-head exists for the single pair
    assert len(result["head_to_head"]) == 1


def test_three_bid_cheapest_headline_loses_when_indemnity_uncapped():
    """A bid that's $50k cheaper but exposes uncapped indemnity (critical) ranks last."""
    expensive_a = {
        "bid_id": "vendor-a",
        "vendor_name": "VendorA",
        "headline_price_cad": 1_050_000.0,
        "clauses": [_liability_clause("liab", severity="medium")],
        "contract_value_cad": 1_000_000.0,
    }
    expensive_b = {
        "bid_id": "vendor-b",
        "vendor_name": "VendorB",
        "headline_price_cad": 1_050_000.0,
        "clauses": [_liability_clause("liab", severity="medium")],
        "contract_value_cad": 1_000_000.0,
    }
    cheap_uncapped = {
        "bid_id": "vendor-c",
        "vendor_name": "CheapVendorC",
        "headline_price_cad": 1_000_000.0,  # $50k cheaper headline
        "clauses": [_liability_clause("liab", severity="critical")],
        "contract_value_cad": 1_000_000.0,
    }

    result = asyncio.run(
        scenario_simulator.simulate_bid_comparison(
            bids=[expensive_a, expensive_b, cheap_uncapped],
            session_data=_session(),
        )
    )

    ranking = {r["bid_id"]: r["rank"] for r in result["ranking"]}
    # The cheap-but-critical vendor should be last on risk-adjusted basis.
    assert ranking["vendor-c"] == 3, (
        f"Expected vendor-c last but got ranking={ranking} | "
        f"weighted={[ (b['bid_id'], b['totals']['weighted_exposure_cad']) for b in result['bids']]}"
    )

    cheap = next(b for b in result["bids"] if b["bid_id"] == "vendor-c")
    expensive = next(b for b in result["bids"] if b["bid_id"] == "vendor-a")
    assert (
        cheap["totals"]["risk_adjusted_total_cost_cad"]
        > expensive["totals"]["risk_adjusted_total_cost_cad"]
    )

    # delta_vs_cheapest narrative populated for non-cheapest bids
    assert cheap["delta_vs_cheapest"] is not None
    assert cheap["delta_vs_cheapest"]["cheapest_bid_id"] == "vendor-c"  # cheap is the cheapest

    # head_to_head: 3 choose 2 = 3 pairs
    assert len(result["head_to_head"]) == 3


def test_dominant_risks_top_three_sorted_by_max_exposure():
    bid = {
        "bid_id": "bid-1",
        "vendor_name": "V1",
        "clauses": [
            _liability_clause("liab", severity="critical"),
            _ip_clause("ip", severity="high"),
            _termination_clause("term", severity="medium"),
        ],
    }
    # Need at least 2 bids to satisfy the comparison contract; mirror the same shape
    bid2 = {
        "bid_id": "bid-2",
        "vendor_name": "V2",
        "clauses": [_liability_clause("liab", severity="low")],
    }

    result = asyncio.run(
        scenario_simulator.simulate_bid_comparison(
            bids=[bid, bid2],
            session_data=_session(),
        )
    )
    out_bid = next(b for b in result["bids"] if b["bid_id"] == "bid-1")
    assert len(out_bid["dominant_risks"]) == 3
    exposures = [r["exposure_max_cad"] for r in out_bid["dominant_risks"]]
    assert exposures == sorted(exposures, reverse=True)


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def http_client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_endpoint_requires_auth(http_client):
    body = {
        "bids": [
            {
                "bid_id": "a",
                "vendor_name": "A",
                "clauses": [_liability_clause("liab")],
            },
            {
                "bid_id": "b",
                "vendor_name": "B",
                "clauses": [_liability_clause("liab")],
            },
        ],
        "session": {"contract_value_cad": 1_000_000.0, "jurisdiction_code": "ON"},
    }
    resp = http_client.post(_ROUTE_PATH, json=body)
    assert resp.status_code == 401, resp.text


def test_endpoint_validation_single_bid_rejected(http_client, auth_headers):
    body = {
        "bids": [
            {
                "bid_id": "a",
                "vendor_name": "A",
                "clauses": [_liability_clause("liab")],
            }
        ],
        "session": {"contract_value_cad": 1_000_000.0, "jurisdiction_code": "ON"},
    }
    resp = http_client.post(_ROUTE_PATH, json=body, headers=auth_headers)
    # Pydantic validation failure → FastAPI returns 422.
    assert resp.status_code in (400, 422), resp.text


def test_endpoint_validation_unknown_scenario_rejected(http_client, auth_headers):
    body = {
        "bids": [
            {
                "bid_id": "a",
                "vendor_name": "A",
                "clauses": [_liability_clause("liab")],
            },
            {
                "bid_id": "b",
                "vendor_name": "B",
                "clauses": [_liability_clause("liab")],
            },
        ],
        "session": {"contract_value_cad": 1_000_000.0, "jurisdiction_code": "ON"},
        "scenarios": ["breach", "armageddon"],
    }
    resp = http_client.post(_ROUTE_PATH, json=body, headers=auth_headers)
    assert resp.status_code in (400, 422), resp.text


def test_endpoint_validation_empty_clauses_rejected(http_client, auth_headers):
    body = {
        "bids": [
            {
                "bid_id": "a",
                "vendor_name": "A",
                "clauses": [],
            },
            {
                "bid_id": "b",
                "vendor_name": "B",
                "clauses": [_liability_clause("liab")],
            },
        ],
        "session": {"contract_value_cad": 1_000_000.0, "jurisdiction_code": "ON"},
    }
    resp = http_client.post(_ROUTE_PATH, json=body, headers=auth_headers)
    assert resp.status_code in (400, 422), resp.text


def test_endpoint_happy_path(http_client, auth_headers):
    body = {
        "bids": [
            {
                "bid_id": "a",
                "vendor_name": "A",
                "headline_price_cad": 1_050_000.0,
                "clauses": [_liability_clause("liab", severity="medium")],
            },
            {
                "bid_id": "b",
                "vendor_name": "B",
                "headline_price_cad": 1_000_000.0,
                "clauses": [_liability_clause("liab", severity="critical")],
            },
        ],
        "session": {"contract_value_cad": 1_000_000.0, "jurisdiction_code": "ON"},
        "scenarios": ["breach", "enforcement"],
    }
    resp = http_client.post(_ROUTE_PATH, json=body, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert {"session", "bids", "ranking", "head_to_head"} <= set(data.keys())
    assert data["session"]["scenarios_run"] == ["breach", "enforcement"]
    assert len(data["bids"]) == 2
    assert len(data["ranking"]) == 2
    assert len(data["head_to_head"]) == 1
    # Ranks are 1 and 2
    assert sorted(r["rank"] for r in data["ranking"]) == [1, 2]
