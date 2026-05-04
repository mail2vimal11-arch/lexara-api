"""Tests for the temporal-graph resolver. Pure algorithm, no DB."""

from datetime import date

from app.services.obligation_resolver import (
    Status,
    resolve_contract_timeline,
)


def _spec(spec_id, obligation_id, **kw):
    base = {
        "spec_id": spec_id,
        "obligation_id": obligation_id,
        "kind": "none",
        "absolute_date": None,
        "offset_value": None,
        "offset_unit": None,
        "direction": None,
        "anchor_id": None,
        "anchor_obligation_id": None,
    }
    base.update(kw)
    return base


def test_absolute_date_resolves_to_itself():
    specs = [_spec("s1", "o1", kind="absolute", absolute_date=date(2026, 5, 1))]
    out = resolve_contract_timeline(specs, anchors={}, holidays=set())
    assert out["s1"].status is Status.RESOLVED
    assert out["s1"].projected_date == date(2026, 5, 1)


def test_relative_to_anchor_resolves_when_anchor_known():
    specs = [_spec("s1", "o1",
        kind="relative", offset_value=30, offset_unit="calendar_days",
        direction="after", anchor_id="a1")]
    out = resolve_contract_timeline(
        specs, anchors={"a1": date(2026, 5, 1)}, holidays=set())
    assert out["s1"].projected_date == date(2026, 5, 31)
    assert out["s1"].dependency_path == ["anchor:a1"]


def test_relative_to_anchor_pending_when_anchor_unknown():
    specs = [_spec("s1", "o1",
        kind="relative", offset_value=30, offset_unit="calendar_days",
        direction="after", anchor_id="a1")]
    out = resolve_contract_timeline(specs, anchors={}, holidays=set())
    assert out["s1"].status is Status.PENDING_ANCHOR


def test_business_days_skip_weekends():
    specs = [_spec("s1", "o1",
        kind="relative", offset_value=5, offset_unit="business_days",
        direction="after", anchor_id="a1")]
    out = resolve_contract_timeline(
        specs, anchors={"a1": date(2026, 5, 1)}, holidays=set())
    assert out["s1"].projected_date == date(2026, 5, 8)


def test_business_days_skip_holidays():
    specs = [_spec("s1", "o1",
        kind="relative", offset_value=5, offset_unit="business_days",
        direction="after", anchor_id="a1")]
    out = resolve_contract_timeline(
        specs, anchors={"a1": date(2026, 5, 15)},
        holidays={date(2026, 5, 18)})
    assert out["s1"].projected_date == date(2026, 5, 25)


def test_chained_obligations_propagate_dates():
    specs = [
        _spec("s1", "o1",
            kind="relative", offset_value=30, offset_unit="calendar_days",
            direction="after", anchor_id="a_award"),
        _spec("s2", "o2",
            kind="relative", offset_value=5, offset_unit="calendar_days",
            direction="after", anchor_obligation_id="o1"),
    ]
    out = resolve_contract_timeline(
        specs, anchors={"a_award": date(2026, 5, 1)}, holidays=set())
    assert out["s1"].projected_date == date(2026, 5, 31)
    assert out["s2"].projected_date == date(2026, 6, 5)
    assert out["s2"].dependency_path == ["anchor:a_award", "obligation:o1"]


def test_chained_pending_propagates():
    specs = [
        _spec("s1", "o1",
            kind="relative", offset_value=30, offset_unit="calendar_days",
            direction="after", anchor_id="a_award"),
        _spec("s2", "o2",
            kind="relative", offset_value=5, offset_unit="calendar_days",
            direction="after", anchor_obligation_id="o1"),
    ]
    out = resolve_contract_timeline(specs, anchors={}, holidays=set())
    assert out["s1"].status is Status.PENDING_ANCHOR
    assert out["s2"].status is Status.PENDING_ANCHOR


def test_cycle_detection_marks_cyclic():
    specs = [
        _spec("s1", "o1",
            kind="relative", offset_value=10, offset_unit="calendar_days",
            direction="after", anchor_obligation_id="o2"),
        _spec("s2", "o2",
            kind="relative", offset_value=10, offset_unit="calendar_days",
            direction="after", anchor_obligation_id="o1"),
    ]
    out = resolve_contract_timeline(specs, anchors={}, holidays=set())
    assert out["s1"].status is Status.CYCLIC
    assert out["s2"].status is Status.CYCLIC


def test_direction_before_subtracts():
    specs = [_spec("s1", "o1",
        kind="relative", offset_value=10, offset_unit="calendar_days",
        direction="before", anchor_id="go_live")]
    out = resolve_contract_timeline(
        specs, anchors={"go_live": date(2026, 6, 15)}, holidays=set())
    assert out["s1"].projected_date == date(2026, 6, 5)


def test_month_offset_clamps_short_months():
    specs = [_spec("s1", "o1",
        kind="relative", offset_value=1, offset_unit="months",
        direction="after", anchor_id="a1")]
    out = resolve_contract_timeline(
        specs, anchors={"a1": date(2026, 1, 31)}, holidays=set())
    assert out["s1"].projected_date == date(2026, 2, 28)
