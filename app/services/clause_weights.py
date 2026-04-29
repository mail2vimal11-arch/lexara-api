"""
Clause weight + move-quality calibration.

Single source of truth for the numeric constants that several services
(`negotiation_ai`, `batna_engine`, `linter_service`) had been re-deriving
inline. Centralising them here keeps the dollar-value math, BATNA leverage,
and the move-quality label that the ledger surfaces consistent.

The weights are advisory strategic weights — they do NOT replace
`risk_exposure_cad`, which remains the user-facing financial number.
"""

from typing import Optional


# ---------------------------------------------------------------------------
# Per-clause-type strategic weight (0–1000)
# ---------------------------------------------------------------------------
# How much a single concession on this clause type shifts the overall
# negotiation. Calibrated against the historical clause types already used
# throughout `negotiation_ai.py` (TRADE_PAIR_SUCCESS_RATES, GOVERNMENT_NON_NEGOTIABLES).

CLAUSE_TYPE_WEIGHT: dict[str, int] = {
    "indemnification": 900,
    "indemnity": 900,
    "limitation_of_liability": 700,
    "liability_cap": 700,
    "liability": 700,
    "ip_ownership": 600,
    "crown_ip_vesting": 600,
    "data_residency": 500,
    "privacy_act_compliance": 500,
    "atip_compliance": 500,
    "audit_rights": 450,
    "warranty": 400,
    "termination": 350,
    "sla": 300,
    "acceptance_criteria": 300,
    "payment_terms": 200,
    "notice_period": 100,
}

DEFAULT_CLAUSE_WEIGHT = 250


def clause_weight(clause_type: Optional[str]) -> int:
    """Return the strategic weight for a clause type. Falls back to default."""
    if not clause_type:
        return DEFAULT_CLAUSE_WEIGHT
    return CLAUSE_TYPE_WEIGHT.get(clause_type.lower(), DEFAULT_CLAUSE_WEIGHT)


# ---------------------------------------------------------------------------
# Severity → numeric score
# ---------------------------------------------------------------------------

SEVERITY_NUMERIC: dict[str, float] = {
    "low": 0.30,
    "medium": 0.60,
    "high": 1.00,
    "critical": 1.00,
}


def severity_to_score(severity: Optional[str]) -> float:
    """Map a severity label to a 0–1 score. Defaults to medium."""
    if not severity:
        return SEVERITY_NUMERIC["medium"]
    return SEVERITY_NUMERIC.get(severity.lower(), SEVERITY_NUMERIC["medium"])


# ---------------------------------------------------------------------------
# Action → expected risk-recovery multiplier
# ---------------------------------------------------------------------------
# Used by `calculate_round_dollar_value` in negotiation_ai. Previously inlined.

ACTION_RECOVERY_MULTIPLIER: dict[str, float] = {
    "accept": 0.70,
    "counter": 0.30,
    "reject": 0.00,
    "trade_offer": 0.00,  # value is realised when the trade resolves
    "propose": 0.00,
}


def action_recovery(action: Optional[str]) -> float:
    """Return the share of risk_exposure recovered for a given action."""
    if not action:
        return 0.0
    return ACTION_RECOVERY_MULTIPLIER.get(action, 0.0)


# ---------------------------------------------------------------------------
# Move-quality classification
# ---------------------------------------------------------------------------
# Four-bucket label exposed on the ledger. Combines:
#   - the action taken (accept / counter / reject / trade_offer)
#   - the LLM's `ai_confidence` from the rule layer
#   - the strategic weight of the clause
# Quality is only meaningful for opponent rounds; user-side `propose`
# rounds return None — quality emerges from the response.

MOVE_QUALITY_LABELS = ("best", "acceptable", "risky", "critical")


def classify_move(
    action: Optional[str],
    ai_confidence: Optional[float],
    clause_type: Optional[str],
    risk_severity: Optional[str] = None,
) -> Optional[str]:
    """
    Derive a four-bucket move-quality label for a negotiation round.

    Returns one of: "best", "acceptable", "risky", "critical".
    Returns None for actions that have no derivable quality yet
    (e.g. the user's own `propose` round — quality is set when the
    opponent responds).
    """
    if action in (None, "propose"):
        return None

    confidence = float(ai_confidence) if ai_confidence is not None else 0.5
    weight = clause_weight(clause_type)
    is_heavy = weight >= 500
    severity_score = severity_to_score(risk_severity)

    if action == "accept":
        return "best" if confidence >= 0.65 else "acceptable"

    if action == "trade_offer":
        return "acceptable"

    if action == "counter":
        if confidence >= 0.55:
            return "acceptable"
        if is_heavy and severity_score >= 0.6:
            return "risky"
        return "acceptable"

    if action == "reject":
        if is_heavy and severity_score >= 0.6:
            return "critical"
        return "risky"

    return None
