"""Resolve a contract's temporal dependency graph.

Given the spec rows (formulas) and known anchor dates, project every deadline.
Topo-sorts the DAG, walks it once, returns one Resolution per spec.

Pure-function resolver: no DB calls inside. Caller fetches the inputs, calls
`resolve_contract_timeline`, and writes the resulting rows to
`obligation_temporal_resolutions`.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Iterable


class Status(str, Enum):
    RESOLVED       = "resolved"
    PENDING_ANCHOR = "pending_anchor"
    CYCLIC         = "cyclic"
    AMBIGUOUS      = "ambiguous"


@dataclass
class Resolution:
    spec_id: str
    projected_date: date | None
    status: Status
    dependency_path: list[str] = field(default_factory=list)


def resolve_contract_timeline(
    specs: Iterable[dict],
    anchors: dict[str, date | None],
    holidays: set[date],
) -> dict[str, Resolution]:
    specs = list(specs)
    spec_by_id  = {s["spec_id"]: s for s in specs}
    spec_by_obl = {s["obligation_id"]: s for s in specs}

    edges_out: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {s["spec_id"]: 0 for s in specs}

    for s in specs:
        upstream_obl = s.get("anchor_obligation_id")
        if s.get("kind") == "relative" and upstream_obl:
            upstream_spec = spec_by_obl.get(upstream_obl)
            if upstream_spec:
                edges_out[upstream_spec["spec_id"]].append(s["spec_id"])
                in_degree[s["spec_id"]] += 1

    queue: deque[str] = deque(sid for sid, deg in in_degree.items() if deg == 0)
    order: list[str] = []
    while queue:
        sid = queue.popleft()
        order.append(sid)
        for downstream in edges_out[sid]:
            in_degree[downstream] -= 1
            if in_degree[downstream] == 0:
                queue.append(downstream)

    cyclic_ids = {s["spec_id"] for s in specs} - set(order)

    out: dict[str, Resolution] = {}

    for sid in order:
        s = spec_by_id[sid]
        kind = s.get("kind", "none")

        if kind == "none":
            out[sid] = Resolution(sid, None, Status.RESOLVED)
            continue

        if kind == "absolute":
            out[sid] = Resolution(sid, s.get("absolute_date"), Status.RESOLVED)
            continue

        if kind == "relative":
            anchor_date, path = _resolve_anchor_date(s, anchors, out, spec_by_obl)
            if anchor_date is None:
                out[sid] = Resolution(sid, None, Status.PENDING_ANCHOR, path)
                continue

            offset = (s.get("offset_value") or 0)
            if s.get("direction") == "before":
                offset = -offset
            projected = _apply_offset(anchor_date, offset, s.get("offset_unit"), holidays)
            out[sid] = Resolution(sid, projected, Status.RESOLVED, path)
            continue

        out[sid] = Resolution(sid, None, Status.AMBIGUOUS)

    for sid in cyclic_ids:
        out[sid] = Resolution(sid, None, Status.CYCLIC)

    return out


def _resolve_anchor_date(spec, anchors, resolved, spec_by_obl):
    if spec.get("anchor_id"):
        aid = spec["anchor_id"]
        return anchors.get(aid), [f"anchor:{aid}"]

    upstream_obl = spec.get("anchor_obligation_id")
    if upstream_obl:
        upstream_spec = spec_by_obl.get(upstream_obl)
        if not upstream_spec:
            return None, [f"obligation:{upstream_obl} (missing)"]
        upstream_res = resolved.get(upstream_spec["spec_id"])
        if upstream_res and upstream_res.projected_date:
            return (
                upstream_res.projected_date,
                upstream_res.dependency_path + [f"obligation:{upstream_obl}"],
            )
        return None, [f"obligation:{upstream_obl} (pending)"]

    return None, []


def _apply_offset(start, n, unit, holidays):
    if unit in (None, "calendar_days"):
        return start + timedelta(days=n)
    if unit == "weeks":
        return start + timedelta(weeks=n)
    if unit == "months":
        return _add_months(start, n)
    if unit == "business_days":
        return _add_business_days(start, n, holidays)
    raise ValueError(f"Unknown offset_unit: {unit!r}")


def _add_business_days(start, n, holidays):
    if n == 0:
        return start
    step = 1 if n > 0 else -1
    remaining = abs(n)
    cur = start
    while remaining:
        cur += timedelta(days=step)
        if cur.weekday() < 5 and cur not in holidays:
            remaining -= 1
    return cur


def _add_months(start, n):
    month_index = start.month - 1 + n
    year  = start.year + month_index // 12
    month = month_index % 12 + 1
    day   = min(start.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year, month):
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day
