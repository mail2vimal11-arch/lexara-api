"""End-to-end tests for the Obligation Matrix temporal routes.

Stubs `extract_temporal_spec` so we exercise the wiring (extract → DB →
resolver → DB → response) without needing the spaCy model. The extractor's
own behavior is covered by unit tests against its patterns.
"""

from __future__ import annotations

import pytest


# ---------- Fixtures ----------

@pytest.fixture
def stub_extractor(monkeypatch):
    """Map known sentence shapes to deterministic specs."""
    def fake_extract(text: str) -> dict:
        t = text.lower()
        base = {
            "kind": "none",
            "absolute_date": None,
            "offset_value": None,
            "offset_unit": None,
            "direction": None,
            "anchor_key": None,
            "anchor_obligation_id": None,
            "raw_phrase": None,
            "confidence": 1.0,
            "recurrence_rule": None,
        }
        if "30 days of contract award" in t or "30 days of award" in t:
            return {**base, "kind": "relative", "offset_value": 30,
                    "offset_unit": "calendar_days", "direction": "after",
                    "anchor_key": "contract_award",
                    "raw_phrase": "within 30 days of contract award",
                    "confidence": 0.9}
        if "5 business days" in t:
            return {**base, "kind": "relative", "offset_value": 5,
                    "offset_unit": "business_days", "direction": "after",
                    "anchor_key": "acceptance",
                    "raw_phrase": "within 5 business days of acceptance",
                    "confidence": 0.85}
        return base

    import app.nlp.temporal_extractor as mod
    monkeypatch.setattr(mod, "extract_temporal_spec", fake_extract)
    yield


@pytest.fixture
def contract_id():
    import uuid
    return f"ct_{uuid.uuid4().hex[:8]}"


# ---------- Tests ----------

def test_analyze_persists_and_returns_pending_when_anchors_unknown(
    client, auth_headers, stub_extractor, contract_id,
):
    payload = {
        "document_text": (
            "1.1 The Contractor shall submit the report within 30 days of contract award. "
            "1.2 The Contractor must remediate within 5 business days of acceptance."
        ),
        "meta": {
            "contract_id": contract_id,
            "known_vendor_entities": ["Contractor"],
        },
    }
    r = client.post("/v1/procurement/obligations/analyze",
                    json=payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["obligations_extracted"] == 2
    timeline = data["timeline"]
    assert len(timeline) == 2

    # Anchors not yet provided -> all relative deadlines pending.
    statuses = {row["status"] for row in timeline}
    assert statuses == {"pending_anchor"}
    assert all(row["projected_date"] is None for row in timeline)


def test_patch_anchors_resolves_dates(
    client, auth_headers, stub_extractor, contract_id,
):
    # Seed the contract.
    client.post("/v1/procurement/obligations/analyze",
        json={
            "document_text": "1.1 The Contractor shall submit the report within 30 days of contract award.",
            "meta": {"contract_id": contract_id, "known_vendor_entities": ["Contractor"]},
        },
        headers=auth_headers,
    )

    # Fill in the contract_award anchor.
    r = client.patch(
        f"/v1/procurement/obligations/contracts/{contract_id}/anchors",
        json={"anchors": [{"anchor_key": "contract_award", "resolved_date": "2026-05-01"}]},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text

    timeline = r.json()["timeline"]
    assert len(timeline) == 1
    row = timeline[0]
    assert row["status"] == "resolved"
    assert row["projected_date"] == "2026-05-31"
    assert "anchor:" in row["dependency_path"][0]


def test_get_timeline_404_when_unknown_contract(client, auth_headers):
    r = client.get(
        "/v1/procurement/obligations/contracts/ct_doesnotexist/timeline",
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_reanalyze_replaces_prior_obligations(
    client, auth_headers, stub_extractor, contract_id,
):
    # First pass: 2 obligations.
    r = client.post("/v1/procurement/obligations/analyze",
        json={
            "document_text": (
                "1.1 The Contractor shall submit within 30 days of contract award. "
                "1.2 The Contractor must remediate within 5 business days of acceptance."
            ),
            "meta": {"contract_id": contract_id, "known_vendor_entities": ["Contractor"]},
        },
        headers=auth_headers,
    )
    assert r.json()["obligations_extracted"] == 2

    # Re-analyze with shorter doc: should be 1 obligation, not 3.
    r = client.post("/v1/procurement/obligations/analyze",
        json={
            "document_text": "1.1 The Contractor shall submit within 30 days of contract award.",
            "meta": {"contract_id": contract_id, "known_vendor_entities": ["Contractor"]},
        },
        headers=auth_headers,
    )
    assert r.json()["obligations_extracted"] == 1
    assert len(r.json()["timeline"]) == 1
