"""
BATNA Engine — Best Alternative to Negotiated Agreement calculator.

Updated after every round. Drives strategic advice shown in the UI intelligence panel.

The BATNA score (0-100) models how attractive the walk-away alternative is for
each party. A high BATNA score means a party can credibly threaten to walk away;
a low BATNA score means they need the deal more than they want to admit.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Re-tender cost and duration benchmarks
# ---------------------------------------------------------------------------

# Tuple: (max_contract_value_exclusive, re_tender_cost_cad, re_tender_weeks)
# Evaluated in order; last entry is the catch-all for >= 5M contracts.
RE_TENDER_BENCHMARKS = [
    (100_000, 25_000, 8),
    (1_000_000, 65_000, 12),
    (5_000_000, 120_000, 16),
    (float("inf"), 200_000, 24),
]


def _leverage_label(score: float) -> str:
    """Convert a numeric BATNA score to a qualitative leverage descriptor."""
    if score > 70:
        return "strong"
    elif score >= 40:
        return "moderate"
    elif score >= 20:
        return "weak"
    else:
        return "critical"


def _re_tender_estimates(contract_value_cad: float) -> tuple[float, int]:
    """Return (cost_cad, weeks) for a hypothetical re-tender of this contract."""
    for max_val, cost, weeks in RE_TENDER_BENCHMARKS:
        if contract_value_cad < max_val:
            return float(cost), weeks
    # Unreachable — last benchmark has max_val=inf — but satisfies type checker
    return 200_000.0, 24


# ---------------------------------------------------------------------------
# User BATNA score
# ---------------------------------------------------------------------------


def _calculate_user_batna(
    session_data: dict,
    clauses: list,
) -> float:
    """
    Compute the user's BATNA score (0-100).

    Inputs from session_data:
        vendor_count_estimate       : int
        fiscal_quarter_end_pressure : bool
        party_type                  : str
        rounds_completed            : int
        total_risk_reduction_cad    : float
        total_concessions_cad       : float
    """
    vendor_count: int = int(session_data.get("vendor_count_estimate") or 1)
    fiscal_pressure: bool = bool(session_data.get("fiscal_quarter_end_pressure", False))
    party_type: str = session_data.get("party_type", "")
    rounds_completed: int = int(session_data.get("rounds_completed") or 0)
    total_risk_reduction: float = float(session_data.get("total_risk_reduction_cad") or 0)
    total_concessions: float = float(session_data.get("total_concessions_cad") or 0)

    # Base score from vendor count
    if vendor_count >= 10:
        score = 85.0
    elif vendor_count >= 4:
        score = 65.0
    elif vendor_count >= 2:
        score = 40.0
    else:
        score = 15.0

    # Penalty: fiscal year-end pressure on government buyers
    if fiscal_pressure and party_type == "government_authority":
        score -= 15.0

    # Penalty: non-negotiables that have been conceded (agreed with poor terms)
    for clause in clauses:
        if (
            clause.get("is_user_non_negotiable")
            and clause.get("state") == "agreed"
            and not clause.get("agreed_text")  # agreed without our proposed text = poor terms
        ):
            score -= 12.0

    # Boost: winning the negotiation overall (risk reduction > concessions given)
    if total_risk_reduction > total_concessions:
        score += 10.0

    # Penalty: negotiation fatigue
    if rounds_completed > 8:
        score -= 5.0

    return max(5.0, min(95.0, score))


# ---------------------------------------------------------------------------
# Opponent BATNA score
# ---------------------------------------------------------------------------


def _calculate_opponent_batna(
    session_data: dict,
) -> float:
    """
    Compute the opponent's BATNA score (0-100).

    Inputs from session_data:
        vendor_count_estimate          : int
        contract_value_cad             : float
        opponent_rejection_count_total : int
        fiscal_quarter_end_pressure    : bool
    """
    vendor_count: int = int(session_data.get("vendor_count_estimate") or 1)
    contract_value_cad: float = float(session_data.get("contract_value_cad") or 0)
    rejection_total: int = int(session_data.get("opponent_rejection_count_total") or 0)
    fiscal_pressure: bool = bool(session_data.get("fiscal_quarter_end_pressure", False))

    # Opponent BATNA is inversely related to vendor count:
    #   - Sole-source vendor has maximum leverage (few alternatives for buyer)
    #   - Highly competitive market → vendor has less leverage
    if vendor_count >= 10:
        score = 20.0
    elif vendor_count >= 4:
        score = 40.0
    elif vendor_count >= 2:
        score = 65.0
    else:
        score = 85.0

    # Penalty: high-value contracts are important to win — opponent wants the deal
    if contract_value_cad > 5_000_000:
        score -= 10.0

    # Penalty: excessive rejections signal the opponent needs the deal
    if rejection_total > 5:
        score -= 8.0

    # Penalty: fiscal year-end pressure is felt by both sides
    if fiscal_pressure:
        score -= 5.0

    return max(5.0, min(95.0, score))


# ---------------------------------------------------------------------------
# Strategic advice
# ---------------------------------------------------------------------------


def _window_assessment(user_batna: float, opponent_batna: float) -> str:
    """Tactical recommendation for the current negotiation window."""
    if user_batna > 65 and opponent_batna < 40:
        return "Press harder"
    elif user_batna > 65:
        return "Hold position"
    elif user_batna >= 40:
        return "Hold position"
    elif user_batna >= 20:
        return "Consider accepting"
    else:
        return "Consider accepting"


def _strategic_advice(user_batna: float, opponent_batna: float) -> str:
    """
    Generate a 1-2 sentence plain-English strategic recommendation.
    """
    if user_batna > 70 and opponent_batna < 40:
        return (
            "Your leverage is strong. Hold firm on non-negotiables and consider "
            "pressing for additional concessions on rated requirements."
        )
    elif user_batna > 70 and opponent_batna > 60:
        return (
            "Both parties have alternatives. Focus on trading lower-priority clauses "
            "to move higher-priority ones."
        )
    elif 40 <= user_batna <= 70:
        return (
            "Moderate leverage. Prioritize your non-negotiables and be willing to "
            "trade on everything else."
        )
    elif 20 <= user_batna < 40:
        return (
            "Your walk-away cost is rising. Focus only on the highest-value clauses "
            "and consider accepting on secondary items."
        )
    else:
        return (
            "Critical: walking away is now more costly than accepting. "
            "Seek legal counsel before conceding further."
        )


# ---------------------------------------------------------------------------
# Weakening triggers
# ---------------------------------------------------------------------------


def _find_weakening_triggers(clauses: list, user_batna: float) -> list:
    """
    Return clause_keys that, if conceded, would significantly drop the user's BATNA.

    A clause is a weakening trigger if:
    - It is marked as user non-negotiable, AND
    - It has not yet been agreed, AND
    - Its risk_exposure_cad is in the top tier
    """
    triggers = []
    for clause in clauses:
        if (
            clause.get("is_user_non_negotiable")
            and clause.get("state") not in ("agreed", "withdrawn")
            and float(clause.get("risk_exposure_cad") or 0) > 0
        ):
            triggers.append(clause.get("clause_key"))

    # Sort by risk exposure descending and cap at 3
    def exposure(key: str) -> float:
        for c in clauses:
            if c.get("clause_key") == key:
                return float(c.get("risk_exposure_cad") or 0)
        return 0.0

    triggers.sort(key=exposure, reverse=True)
    return triggers[:3]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_batna(
    session_data: dict,
    clauses: list,
    concession_history: list,
) -> dict:
    """
    Compute full BATNA analysis for both parties and return a rich strategy object.

    Parameters
    ----------
    session_data : dict
        Keys: vendor_count_estimate, contract_value_cad,
              fiscal_quarter_end_pressure, party_type, rounds_completed,
              total_risk_reduction_cad, total_concessions_cad,
              opponent_rejection_count_total
    clauses : list[dict]
        NegotiationClause dicts for this session.
    concession_history : list[dict]
        NegotiationConcession dicts for this session.

    Returns
    -------
    dict
        user_batna_score      : float (0-100)
        opponent_batna_score  : float (0-100)
        user_leverage         : str ("strong" | "moderate" | "weak" | "critical")
        opponent_leverage     : str
        strategic_advice      : str
        weakening_triggers    : list[str]  — clause keys
        window_assessment     : str
        re_tender_cost_estimate : float
        re_tender_weeks_estimate : int
    """
    user_batna = _calculate_user_batna(session_data, clauses)
    opponent_batna = _calculate_opponent_batna(session_data)

    contract_value_cad = float(session_data.get("contract_value_cad") or 0)
    re_tender_cost, re_tender_weeks = _re_tender_estimates(contract_value_cad)

    weakening_triggers = _find_weakening_triggers(clauses, user_batna)

    result = {
        "user_batna_score": round(user_batna, 1),
        "opponent_batna_score": round(opponent_batna, 1),
        "user_leverage": _leverage_label(user_batna),
        "opponent_leverage": _leverage_label(opponent_batna),
        "strategic_advice": _strategic_advice(user_batna, opponent_batna),
        "weakening_triggers": weakening_triggers,
        "window_assessment": _window_assessment(user_batna, opponent_batna),
        "re_tender_cost_estimate": re_tender_cost,
        "re_tender_weeks_estimate": re_tender_weeks,
    }

    logger.debug(
        f"BATNA calculated: user={user_batna:.1f} ({result['user_leverage']}) "
        f"opponent={opponent_batna:.1f} ({result['opponent_leverage']}) "
        f"window={result['window_assessment']!r}"
    )

    return result
