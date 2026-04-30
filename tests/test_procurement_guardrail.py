"""Fixture-driven tests for ProcurementGuardrail.

Every rule change must keep these green. New rules add new fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.procurement_guardrail import Move, ProcurementGuardrail

RULES_DIR = Path(__file__).parent.parent / "rules"
FIXTURES_PATH = RULES_DIR / "fixtures" / "test_cases.json"


@pytest.fixture(scope="module")
def guardrail() -> ProcurementGuardrail:
    return ProcurementGuardrail.load(RULES_DIR)


@pytest.fixture(scope="module")
def fixture_cases() -> list[dict]:
    return json.loads(FIXTURES_PATH.read_text())["cases"]


def test_rules_load_without_error(guardrail: ProcurementGuardrail) -> None:
    assert guardrail._rules, "no rules loaded"


def test_no_stale_rules(guardrail: ProcurementGuardrail) -> None:
    stale_ids = [r.id for r in guardrail.stale_rules]
    assert not stale_ids, (
        f"these rules have not been reviewed in {ProcurementGuardrail.REVIEW_WINDOW_DAYS}d: {stale_ids}. "
        "Counsel must re-stamp `last_reviewed` or `superseded_by`."
    )


def test_fixture_cases(guardrail: ProcurementGuardrail, fixture_cases: list[dict]) -> None:
    failures: list[str] = []
    for case in fixture_cases:
        move = Move(**case["move"])
        triggers = guardrail.screen(move, case["context"])
        triggered_ids = sorted(t.rule_id for t in triggers)
        expected_ids = sorted(case.get("expected_rule_ids", []))
        if triggered_ids != expected_ids:
            failures.append(
                f"{case['name']}: expected rules {expected_ids}, got {triggered_ids}"
            )
            continue
        is_blocked = guardrail.is_blocked(triggers)
        if case.get("expected_blocked", False) != is_blocked:
            failures.append(
                f"{case['name']}: expected_blocked={case.get('expected_blocked')} got {is_blocked}"
            )
        if case.get("expected_warned"):
            warned = any(t.severity == "soft_warn" for t in triggers)
            if not warned:
                failures.append(f"{case['name']}: expected soft_warn, none seen")
    assert not failures, "fixture mismatches:\n  - " + "\n  - ".join(failures)


def test_duplicate_rule_id_detected(tmp_path: Path) -> None:
    bad = tmp_path / "bad"
    bad.mkdir()
    payload = {
        "rules": [
            _stub_rule("dup-id"),
            _stub_rule("dup-id"),
        ]
    }
    (bad / "a.json").write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="duplicate rule id"):
        ProcurementGuardrail.load(bad)


def _stub_rule(rid: str) -> dict:
    return {
        "id": rid,
        "statute": "TEST",
        "jurisdiction": "CA",
        "section": "s.1",
        "version_as_of": "2024-01-01",
        "effective_date": "2024-01-01",
        "last_reviewed": "2026-01-01",
        "last_reviewed_by": "counsel:test",
        "source_url": "https://example.test",
        "forbid": {"move_types": ["x"], "text_patterns": []},
        "severity": "hard_block",
        "reason": "test",
    }
