"""
Cross-Contract Cascade Detector — Step 2 of the Lexara "Blast Radius" engine.

Pure-Python, deterministic rules over the user's Obligation table. No LLM,
no temporal-graph layer, no per-pair queries: we pull the user's obligations
once (filtered by status of their parent contract) and run three rule
families in memory:

    Rule A — Payment-pair gap (liquidity risk)
            Net-X payable to a vendor lands BEFORE a Net-Y receivable
            from a client → cash gap of (Y - X) days.

    Rule B — Delivery cascade slip
            Counterparty needs as long or longer to deliver to us than
            we have to deliver to our client → schedule slack ≤ 0.

    Rule C — Liability-cap shortfall
            Our exposure on one contract (penalty / indemnity) exceeds
            the vendor's liability cap on another contract → uncovered
            dollars on the table.

Narratives are f-string templated. Severity thresholds are fixed and
documented inline so the math is auditable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.obligation import Obligation
from app.models.portfolio_contract import PortfolioContract


# ---------------------------------------------------------------------------
# Severity ordering — used for sort
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _triggers_aligned(a: Obligation, b: Obligation) -> bool:
    """
    Two obligations share an "aligned trigger" if either:
      - they have the exact same trigger_event string, or
      - both keys point at the same coarse phase: contract_start
        or a milestone_* prefix.
    """
    ta = (a.trigger_event or "").strip()
    tb = (b.trigger_event or "").strip()
    if ta and tb and ta == tb:
        return True
    aligned_anchors = {"contract_start"}
    if ta in aligned_anchors and tb in aligned_anchors:
        return True
    if ta.startswith("milestone_") and tb.startswith("milestone_"):
        return True
    return False


def _contract_summary(c: PortfolioContract) -> Dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "our_role": c.our_role,
    }


def _obligation_summary(o: Obligation) -> Dict[str, Any]:
    return {
        "id": o.id,
        "obligation_type": o.obligation_type,
        "party": o.party,
        "description": o.description,
    }


def _money(value: Optional[float]) -> str:
    """Render a CAD amount the way the narrative templates want it."""
    if value is None:
        return "an unquantified amount"
    return f"CAD ${value:,.0f}"


# ---------------------------------------------------------------------------
# Rule A — Payment-pair gap (liquidity risk)
# ---------------------------------------------------------------------------

def _rule_payment_gap(
    obligations: List[Obligation],
    contracts_by_id: Dict[str, PortfolioContract],
) -> List[Dict[str, Any]]:
    """
    Find (X, Y) pairs across DIFFERENT contracts where:
        X: payment we owe (party=us), deadline_days_from_trigger=Nx
        Y: payment owed to us (party=counterparty), Ny
        Nx < Ny  AND  triggers aligned
    Liquidity gap = Ny - Nx days.

    Quantification heuristic:
        gap_amount_cad = min(
            X.penalty_amount_cad or X-contract.contract_value_cad,
            Y-contract.contract_value_cad,
        )
    The intent: how much cash do we have to front. We bound it by the
    inflow side because we cannot owe more than the receivable that's
    backing the gap. If neither side has a dollar value the conflict is
    flagged unquantified.
    """
    payables = [
        o for o in obligations
        if o.obligation_type == "payment"
        and o.party == "us"
        and o.deadline_days_from_trigger is not None
    ]
    receivables = [
        o for o in obligations
        if o.obligation_type == "payment"
        and o.party == "counterparty"
        and o.deadline_days_from_trigger is not None
    ]

    out: List[Dict[str, Any]] = []
    for x in payables:
        for y in receivables:
            if x.contract_id == y.contract_id:
                continue  # intra-contract — different feature
            if x.deadline_days_from_trigger >= y.deadline_days_from_trigger:
                continue
            if not _triggers_aligned(x, y):
                continue

            gap_days = y.deadline_days_from_trigger - x.deadline_days_from_trigger

            cx = contracts_by_id.get(x.contract_id)
            cy = contracts_by_id.get(y.contract_id)
            if cx is None or cy is None:
                continue

            # Quantify using the heuristic documented in the docstring.
            x_side = x.penalty_amount_cad or cx.contract_value_cad
            y_side = cy.contract_value_cad
            if x_side is not None and y_side is not None:
                gap_amount_cad: Optional[float] = float(min(x_side, y_side))
            elif x_side is not None:
                gap_amount_cad = float(x_side)
            elif y_side is not None:
                gap_amount_cad = float(y_side)
            else:
                gap_amount_cad = None

            # Severity ladder
            if gap_amount_cad is None:
                severity = "critical" if gap_days >= 30 else (
                    "high" if gap_days >= 14 else "medium"
                )
            elif gap_days >= 30 and gap_amount_cad >= 25_000:
                severity = "critical"
            elif gap_days >= 14:
                severity = "high"
            else:
                severity = "medium"

            narrative = (
                f"Net-{y.deadline_days_from_trigger} receivable from "
                f"{cy.counterparty_name} versus Net-{x.deadline_days_from_trigger} "
                f"payable to {cx.counterparty_name} creates a {gap_days}-day "
                f"cash gap of {_money(gap_amount_cad)}."
            )

            out.append({
                "conflict_type": "payment_gap",
                "severity": severity,
                "contracts": [_contract_summary(cx), _contract_summary(cy)],
                "obligations": [_obligation_summary(x), _obligation_summary(y)],
                "gap_days": gap_days,
                "gap_amount_cad": gap_amount_cad,
                "narrative": narrative,
            })

    return out


# ---------------------------------------------------------------------------
# Rule B — Delivery cascade slip
# ---------------------------------------------------------------------------

def _rule_delivery_slip(
    obligations: List[Obligation],
    contracts_by_id: Dict[str, PortfolioContract],
) -> List[Dict[str, Any]]:
    """
    Pairs across DIFFERENT contracts where:
        X: delivery we owe (party=us), Nx
        Y: delivery owed to us (party=counterparty), Ny
        Ny >= Nx  → counterparty needs at least as long as we have.
    Slack = Nx - Ny (zero or negative on a slip).

    Exposure quantified from X.penalty_amount_cad (downstream LDs).
    """
    we_deliver = [
        o for o in obligations
        if o.obligation_type == "delivery"
        and o.party == "us"
        and o.deadline_days_from_trigger is not None
    ]
    they_deliver = [
        o for o in obligations
        if o.obligation_type == "delivery"
        and o.party == "counterparty"
        and o.deadline_days_from_trigger is not None
    ]

    out: List[Dict[str, Any]] = []
    for x in we_deliver:
        for y in they_deliver:
            if x.contract_id == y.contract_id:
                continue
            if y.deadline_days_from_trigger < x.deadline_days_from_trigger:
                continue  # vendor faster than client deadline → fine

            slack = x.deadline_days_from_trigger - y.deadline_days_from_trigger

            cx = contracts_by_id.get(x.contract_id)
            cy = contracts_by_id.get(y.contract_id)
            if cx is None or cy is None:
                continue

            gap_amount_cad = (
                float(x.penalty_amount_cad)
                if x.penalty_amount_cad is not None
                else None
            )

            if slack <= 0:
                severity = "critical"
            elif slack <= 5:
                severity = "high"
            else:
                severity = "medium"

            narrative = (
                f"We owe {cx.counterparty_name} delivery in "
                f"{x.deadline_days_from_trigger} days, but "
                f"{cy.counterparty_name} only commits to delivering to us in "
                f"{y.deadline_days_from_trigger} days "
                f"(slack {slack} days). Downstream LD exposure: "
                f"{_money(gap_amount_cad)}."
            )

            out.append({
                "conflict_type": "delivery_slip",
                "severity": severity,
                "contracts": [_contract_summary(cx), _contract_summary(cy)],
                "obligations": [_obligation_summary(x), _obligation_summary(y)],
                "gap_days": slack,
                "gap_amount_cad": gap_amount_cad,
                "narrative": narrative,
            })

    return out


# ---------------------------------------------------------------------------
# Rule C — Liability-cap shortfall
# ---------------------------------------------------------------------------

_PRIME_ROLES = {"prime", "seller"}
_VENDOR_BUYER_ROLES = {"buyer", "prime"}


def _rule_liability_shortfall(
    obligations: List[Obligation],
    contracts_by_id: Dict[str, PortfolioContract],
) -> List[Dict[str, Any]]:
    """
    For each X where party=us, obligation is indemnity OR has a sizable
    penalty_amount_cad, and the parent contract has us as prime/seller
    (i.e. we owe the client). Then look for a counterparty obligation Y
    on a DIFFERENT contract where:
        - we are the buyer/prime of that vendor,
        - Y.liability_cap_cad < X.penalty_amount_cad.
    Uncovered = X.penalty_amount_cad - Y.liability_cap_cad.
    """
    our_exposures = []
    for o in obligations:
        if o.party != "us":
            continue
        if o.obligation_type != "indemnity" and not o.penalty_amount_cad:
            continue
        if o.penalty_amount_cad is None:
            continue
        c = contracts_by_id.get(o.contract_id)
        if c is None or c.our_role not in _PRIME_ROLES:
            continue
        our_exposures.append(o)

    vendor_caps = []
    for o in obligations:
        if o.party != "counterparty":
            continue
        if o.liability_cap_cad is None:
            continue
        c = contracts_by_id.get(o.contract_id)
        if c is None or c.our_role not in _VENDOR_BUYER_ROLES:
            continue
        vendor_caps.append(o)

    out: List[Dict[str, Any]] = []
    for x in our_exposures:
        for y in vendor_caps:
            if x.contract_id == y.contract_id:
                continue
            if y.liability_cap_cad >= x.penalty_amount_cad:
                continue

            uncovered = float(x.penalty_amount_cad) - float(y.liability_cap_cad)

            cx = contracts_by_id.get(x.contract_id)
            cy = contracts_by_id.get(y.contract_id)
            if cx is None or cy is None:
                continue

            if uncovered >= 100_000:
                severity = "critical"
            elif uncovered >= 25_000:
                severity = "high"
            else:
                severity = "medium"

            narrative = (
                f"Our exposure to {cx.counterparty_name} is "
                f"{_money(float(x.penalty_amount_cad))}, but vendor "
                f"{cy.counterparty_name}'s liability cap is "
                f"{_money(float(y.liability_cap_cad))} — "
                f"{_money(uncovered)} of uncovered exposure on our books."
            )

            out.append({
                "conflict_type": "liability_shortfall",
                "severity": severity,
                "contracts": [_contract_summary(cx), _contract_summary(cy)],
                "obligations": [_obligation_summary(x), _obligation_summary(y)],
                "gap_days": None,
                "gap_amount_cad": uncovered,
                "narrative": narrative,
            })

    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_cascades(
    db: Session,
    user_id: str,
    focus_contract_id: Optional[str] = None,
    include_draft: bool = False,
) -> Dict[str, Any]:
    """
    Detect cross-contract cascade conflicts for one user.

    Args:
        db: SQLAlchemy session.
        user_id: stringified user UUID — filtered against the indexed
            obligations.user_id / portfolio_contracts.user_id columns.
        focus_contract_id: if set, only conflicts that touch this contract
            are returned. (The full set is computed first; we filter at
            the end so cross-contract math stays sane.)
        include_draft: if False (default), only "active" contracts are
            scanned. If True, "draft" contracts are also included — useful
            for "what would happen if I sign this?" simulations.

    Returns the dict shape documented in the module docstring.
    """
    statuses: Tuple[str, ...] = ("active",) if not include_draft else ("active", "draft")

    contracts: List[PortfolioContract] = (
        db.query(PortfolioContract)
        .filter(
            PortfolioContract.user_id == user_id,
            PortfolioContract.status.in_(statuses),
        )
        .all()
    )
    contracts_by_id: Dict[str, PortfolioContract] = {c.id: c for c in contracts}
    eligible_contract_ids = set(contracts_by_id.keys())

    if not eligible_contract_ids:
        return {
            "user_id": user_id,
            "focus_contract_id": focus_contract_id,
            "conflicts": [],
            "totals": {
                "total_conflicts": 0,
                "by_severity": {"critical": 0, "high": 0, "medium": 0},
                "total_quantified_exposure_cad": 0.0,
                "total_unquantified_conflicts": 0,
            },
        }

    obligations: List[Obligation] = (
        db.query(Obligation)
        .filter(
            Obligation.user_id == user_id,
            Obligation.contract_id.in_(eligible_contract_ids),
        )
        .all()
    )

    conflicts: List[Dict[str, Any]] = []
    conflicts.extend(_rule_payment_gap(obligations, contracts_by_id))
    conflicts.extend(_rule_delivery_slip(obligations, contracts_by_id))
    conflicts.extend(_rule_liability_shortfall(obligations, contracts_by_id))

    # Focus-mode: only conflicts touching the focus contract.
    if focus_contract_id is not None:
        conflicts = [
            c for c in conflicts
            if any(ct["id"] == focus_contract_id for ct in c["contracts"])
        ]

    # Sort: severity (critical first), then gap_amount_cad desc (None last).
    conflicts.sort(
        key=lambda c: (
            _SEVERITY_ORDER.get(c["severity"], 99),
            -(c["gap_amount_cad"] if c["gap_amount_cad"] is not None else -1),
        )
    )

    by_severity = {"critical": 0, "high": 0, "medium": 0}
    total_quantified = 0.0
    total_unquantified = 0
    for c in conflicts:
        by_severity[c["severity"]] = by_severity.get(c["severity"], 0) + 1
        if c["gap_amount_cad"] is None:
            total_unquantified += 1
        else:
            total_quantified += float(c["gap_amount_cad"])

    return {
        "user_id": user_id,
        "focus_contract_id": focus_contract_id,
        "conflicts": conflicts,
        "totals": {
            "total_conflicts": len(conflicts),
            "by_severity": by_severity,
            "total_quantified_exposure_cad": total_quantified,
            "total_unquantified_conflicts": total_unquantified,
        },
    }
