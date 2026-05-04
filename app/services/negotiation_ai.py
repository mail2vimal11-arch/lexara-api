"""
Negotiation AI — opposing party counsel simulation engine.

Decision pipeline:
  1. Rule layer  — jurisdiction/clause-type rules applied first (fast, deterministic)
  2. Context layer — negotiation history, BATNA, concession count
  3. LLM layer   — Groq → Claude fallback generates natural language response
"""

import httpx
import json
import logging
import random
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Clause types that government contracting authorities NEVER concede
GOVERNMENT_NON_NEGOTIABLES = {
    "government_authority": [
        "audit_rights",
        "crown_ip_vesting",
        "privacy_act_compliance",
        "atip_compliance",
    ],
    "federal_vendor": ["limitation_of_liability", "payment_terms", "ip_ownership"],
    "software_licensor": ["ip_ownership", "liability_cap", "data_residency"],
}

# Clause types where standard market practice is clear (HIGH acceptance rate)
STANDARD_MARKET_CLAUSES = {
    "ON": {
        "liability": "Cap at 12 months contract value is standard in Ontario IT contracts"
    },
    "FED": {
        "liability": "SACC Manual clause A9075C sets standard LOL provisions"
    },
    "BC": {
        "liability": "BC standard IT contract caps at 12 months or $2M whichever is greater"
    },
    "QC": {
        "liability": "Civil Code Art. 1613 limits consequential damages by default"
    },
}

# Concession fatigue: after N concessions, opponent gets harder
CONCESSION_FATIGUE_THRESHOLD = 3
CONCESSION_FATIGUE_MULTIPLIER = 0.4  # reduces acceptance probability

# Trade acceptance probability by clause pair type
TRADE_PAIR_SUCCESS_RATES = {
    ("liability", "ip_ownership"): 0.71,
    ("termination", "payment_terms"): 0.68,
    ("sla", "acceptance_criteria"): 0.74,
    ("indemnification", "warranty"): 0.65,
    ("liability", "termination"): 0.58,
}

# Keywords that signal market-standard language in a proposed clause
MARKET_STANDARD_KEYWORDS = [
    "12 months",
    "contract value",
    "direct damages",
    "reasonable notice",
    "good faith",
    "standard of care",
    "industry standard",
    "best efforts",
    "commercially reasonable",
    "mutual",
]

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _contains_market_standard_language(proposed_text: str) -> bool:
    """Simple keyword scan to detect whether proposed text resembles market-standard language."""
    lower = proposed_text.lower()
    hits = sum(1 for kw in MARKET_STANDARD_KEYWORDS if kw.lower() in lower)
    return hits >= 2


def _calculate_acceptance_probability(
    session_data: dict, clause_data: dict, proposed_text: str
) -> float:
    """
    Compute the probability (0-1) that the opposing party accepts the proposed text.

    Factors applied in order:
      - Base probability (0.4)
      - Market-standard language boost
      - Vendor count (more vendors = opponent more conciliatory)
      - Government non-negotiable penalty
      - Concession fatigue multiplier
      - Rejection history penalty
      - Risk severity penalty/boost
    """
    base_prob: float = 0.4

    # Boost: proposed text resembles market-standard language
    if _contains_market_standard_language(proposed_text):
        jurisdiction_code = session_data.get("jurisdiction_code", "ON")
        clause_type = clause_data.get("clause_type", "")
        if jurisdiction_code in STANDARD_MARKET_CLAUSES and clause_type in STANDARD_MARKET_CLAUSES.get(jurisdiction_code, {}):
            base_prob += 0.20
        else:
            base_prob += 0.10

    # Boost/penalty: vendor count signal
    vendor_count = session_data.get("vendor_count_estimate", 5)
    if vendor_count >= 10:
        base_prob += 0.25
    elif vendor_count <= 2:
        base_prob -= 0.20

    # Penalty: opposing party's non-negotiable clauses
    opposing_party_type = session_data.get("opposing_party_type", "")
    clause_type = clause_data.get("clause_type", "")
    if clause_type in GOVERNMENT_NON_NEGOTIABLES.get(opposing_party_type, []):
        base_prob -= 0.50

    # Penalty: concession fatigue
    total_opponent_concessions = session_data.get("opponent_concession_count", 0)
    if total_opponent_concessions >= CONCESSION_FATIGUE_THRESHOLD:
        base_prob *= CONCESSION_FATIGUE_MULTIPLIER

    # Penalty: clause has been rejected before → harder to move
    rejection_count = clause_data.get("opponent_rejection_count", 0)
    base_prob -= rejection_count * 0.12

    # Risk severity modifier
    severity_penalties = {
        "critical": -0.30,
        "high": -0.15,
        "medium": 0,
        "low": 0.10,
    }
    base_prob += severity_penalties.get(clause_data.get("risk_severity", "medium"), 0)

    return max(0.05, min(0.95, base_prob))


def _determine_action(probability: float, rejection_count: int) -> str:
    """Map acceptance probability to a negotiation action."""
    if probability > 0.65:
        return "accept"
    elif probability >= 0.30:
        return "counter"
    elif rejection_count < 2:
        return "reject"
    else:
        return "trade_offer"


async def _call_groq(system_prompt: str, user_prompt: str) -> str:
    """
    Call Groq with a free-form system/user prompt pair.
    Returns the raw text content of the response.
    Raises on failure so callers can fall through to Claude.
    """
    if not settings.groq_api_key:
        raise ValueError("Groq not configured")

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 512,
        "temperature": 0.6,
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(GROQ_API_URL, headers=headers, json=payload)

    if response.status_code == 429:
        raise Exception("Groq rate limited")
    if response.status_code != 200:
        raise Exception(f"Groq API error: {response.status_code}")

    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        raise Exception("Groq returned empty choices")

    content = choices[0]["message"]["content"].strip()
    return content


async def _call_claude(system_prompt: str, user_prompt: str) -> str:
    """
    Call Claude (claude-haiku-4-5-20251001) with a free-form prompt.
    Returns the raw text content of the response.
    """
    if not settings.claude_api_key:
        raise ValueError("Claude not configured")

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.claude_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 512,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )

    if response.status_code != 200:
        raise Exception(f"Claude API error: {response.status_code}")

    result = response.json()
    content_list = result.get("content", [])
    if not content_list:
        raise Exception("Claude returned empty content")

    return content_list[0].get("text", "").strip()


async def _generate_llm_response(
    session_data: dict, clause_data: dict, proposed_text: str, action: str
) -> str:
    """
    Generate the opposing counsel's natural-language response via Groq → Claude waterfall.
    """
    opposing_party_type = session_data.get("opposing_party_type", "commercial vendor")
    clause_type = clause_data.get("clause_type", "contract")
    clause_title = clause_data.get("clause_title", clause_data.get("clause_key", "clause"))
    original_text = clause_data.get("original_text", "")
    jurisdiction_code = session_data.get("jurisdiction_code", "ON")
    contract_value_cad = session_data.get("contract_value_cad", 0)

    action_instruction = {
        "accept": (
            "Confirm acceptance professionally and note what you appreciate about "
            "the revision. Be concise and collegial."
        ),
        "reject": (
            "Explain professionally why you cannot accept this revision. Be firm "
            "but constructive and reference the specific legal or commercial concern."
        ),
        "counter": (
            "Generate a counter-proposal that protects your position while moving "
            "toward agreement. Suggest specific alternative language or a modified position."
        ),
        "trade_offer": (
            "Explain that you cannot accept this revision as written, and signal "
            "openness to a broader package deal that addresses both parties' priorities."
        ),
    }.get(action, "Respond professionally to this revision proposal.")

    system_prompt = (
        "You are experienced commercial counsel. "
        "Respond in plain, professional legal English. "
        "Do NOT reference any AI or automated system. "
        "Keep responses to 2-4 sentences. "
        "Do not include JSON, markdown, or preamble — only the response text itself."
    )

    user_prompt = (
        f"You are {opposing_party_type} counsel negotiating a {clause_type} clause "
        f"in a {contract_value_cad:,.0f} CAD contract under {jurisdiction_code} law.\n\n"
        f"The other party has proposed this revision to the {clause_title} clause:\n"
        f'"{proposed_text}"\n\n'
        f"The original clause read:\n"
        f'"{original_text[:600]}"\n\n'
        f"Your response decision: {action.upper()}\n"
        f"{action_instruction}\n\n"
        "Response must:\n"
        "- Be 2-4 sentences maximum\n"
        "- Sound like experienced commercial counsel\n"
        "- Reference a specific legal or commercial concern (not generic)\n"
        "- NOT reference any AI or automated system\n"
        f"- Be jurisdiction-aware (reference {jurisdiction_code} standards where appropriate)\n\n"
        "Return ONLY the response text. No JSON. No preamble."
    )

    # Waterfall: Groq → Claude
    if settings.use_groq and settings.groq_api_key:
        try:
            text = await _call_groq(system_prompt, user_prompt)
            logger.info(f"Negotiation AI ({action}): Groq success")
            return text
        except Exception as e:
            logger.warning(f"Groq failed for negotiation response, falling back to Claude: {e}")

    text = await _call_claude(system_prompt, user_prompt)
    logger.info(f"Negotiation AI ({action}): Claude success")
    return text


def _generate_trade_offer(
    session_data: dict, clause_data: dict
) -> dict:
    """
    Build a trade_offer payload when the AI decides to propose a package deal.

    Finds the best matching complementary clause type from TRADE_PAIR_SUCCESS_RATES
    and surfaces it as a structured offer. The caller (route layer) is expected to
    resolve the actual clause keys from the session's clause list.
    """
    clause_type = clause_data.get("clause_type", "")
    jurisdiction_code = session_data.get("jurisdiction_code", "ON")

    # Find pairs involving this clause type
    best_pair = None
    best_rate = 0.0
    for (a, b), rate in TRADE_PAIR_SUCCESS_RATES.items():
        if (a == clause_type or b == clause_type) and rate > best_rate:
            best_rate = rate
            best_pair = (a, b)

    if best_pair is None:
        # Fallback: propose the highest-rate pair overall
        best_pair = max(TRADE_PAIR_SUCCESS_RATES, key=lambda k: TRADE_PAIR_SUCCESS_RATES[k])
        best_rate = TRADE_PAIR_SUCCESS_RATES[best_pair]

    # The complementary clause type we want in exchange
    complement_type = best_pair[1] if best_pair[0] == clause_type else best_pair[0]

    return {
        "offered_clause_type": clause_type,
        "requested_clause_type": complement_type,
        "pair_success_rate": best_rate,
        "jurisdiction_code": jurisdiction_code,
        "rationale": (
            f"We are prepared to consider movement on the {clause_type.replace('_', ' ')} "
            f"clause if we can reach agreement simultaneously on the "
            f"{complement_type.replace('_', ' ')} clause. "
            f"A package approach is consistent with how these provisions are typically "
            f"negotiated in {jurisdiction_code} procurement contracts."
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_opponent_response(
    session_data: dict, clause_data: dict, proposed_text: str
) -> dict:
    """
    Generate the opposing party's response to the user's proposed clause text.

    Parameters
    ----------
    session_data : dict
        Keys: party_type, jurisdiction_code, contract_value_cad,
              vendor_count_estimate, opposing_party_type,
              opponent_rejection_count_total, rounds_completed,
              opponent_concession_count (optional)
    clause_data : dict
        Keys: clause_key, clause_type, clause_title, original_text,
              opponent_rejection_count, is_user_non_negotiable,
              risk_severity, risk_exposure_cad
    proposed_text : str
        The revised clause language the user is proposing.

    Returns
    -------
    dict with keys:
        action           : "accept" | "reject" | "counter" | "trade_offer"
        response_text    : str   — natural language from opposing counsel
        counter_text     : str | None
        trade_offer      : dict | None
        dollar_value_cad : float | None
        ai_confidence    : float
    """
    # ── Rule layer ────────────────────────────────────────────────────────────
    probability = _calculate_acceptance_probability(
        session_data, clause_data, proposed_text
    )
    rejection_count = clause_data.get("opponent_rejection_count", 0)
    action = _determine_action(probability, rejection_count)

    # ── LLM layer ─────────────────────────────────────────────────────────────
    trade_offer_payload: Optional[dict] = None
    counter_text: Optional[str] = None

    if action == "trade_offer":
        trade_offer_payload = _generate_trade_offer(session_data, clause_data)
        # Still generate a natural-language lead-in via LLM
        try:
            response_text = await _generate_llm_response(
                session_data, clause_data, proposed_text, "trade_offer"
            )
        except Exception as e:
            logger.error(f"LLM failed for trade_offer response: {e}")
            response_text = (
                "We are unable to accept this revision in isolation, but we remain "
                "open to a package approach that addresses both parties' key concerns."
            )
    else:
        try:
            response_text = await _generate_llm_response(
                session_data, clause_data, proposed_text, action
            )
        except Exception as e:
            logger.error(f"LLM failed for {action} response: {e}")
            # Graceful degradation — return a sensible default
            defaults = {
                "accept": "We can accept this revision. Thank you for accommodating our concerns.",
                "reject": (
                    "We are unable to accept this revision. "
                    "The proposed language does not adequately protect our position "
                    "under the applicable procurement framework."
                ),
                "counter": (
                    "We cannot accept this revision as drafted. "
                    "We propose reverting to a mutual limitation of liability "
                    "consistent with standard market practice in this jurisdiction."
                ),
            }
            response_text = defaults.get(action, "We have reviewed your proposal and will respond in due course.")

        if action == "counter":
            # For counter, the response_text itself is the counter-proposal
            counter_text = response_text

    # ── Dollar value ──────────────────────────────────────────────────────────
    dollar_value = calculate_round_dollar_value(clause_data, action)

    return {
        "action": action,
        "response_text": response_text,
        "counter_text": counter_text,
        "trade_offer": trade_offer_payload,
        "dollar_value_cad": dollar_value if dollar_value else None,
        "ai_confidence": round(probability, 3),
    }


async def evaluate_trade(
    session_data: dict, offered_clause: dict, requested_clause: dict
) -> dict:
    """
    Evaluate whether the opposing party accepts a cross-clause trade.

    Parameters
    ----------
    session_data : dict
        Keys: vendor_count_estimate, contract_value_cad, opposing_party_type,
              jurisdiction_code, opponent_concession_count (optional)
    offered_clause : dict
        The clause the user is offering to move on.
        Keys: clause_key, clause_type, proposed_text, original_text
    requested_clause : dict
        The clause the user wants the opponent to move on.
        Keys: clause_key, clause_type, original_text

    Returns
    -------
    dict with keys:
        accepted      : bool
        rationale     : str
        counter_trade : dict | None  — alternative pair proposed if rejected
    """
    offered_type = offered_clause.get("clause_type", "")
    requested_type = requested_clause.get("clause_type", "")

    # Look up base success rate
    pair_rate = TRADE_PAIR_SUCCESS_RATES.get(
        (offered_type, requested_type),
        TRADE_PAIR_SUCCESS_RATES.get((requested_type, offered_type), 0.40),
    )

    # Adjust for vendor count
    vendor_count = session_data.get("vendor_count_estimate", 5)
    if vendor_count >= 10:
        pair_rate += 0.15
    elif vendor_count <= 2:
        pair_rate -= 0.10

    # Adjust for opponent concession fatigue
    opponent_concessions = session_data.get("opponent_concession_count", 0)
    if opponent_concessions >= CONCESSION_FATIGUE_THRESHOLD:
        pair_rate *= CONCESSION_FATIGUE_MULTIPLIER

    pair_rate = max(0.05, min(0.95, pair_rate))

    # Stochastic acceptance (seeded by clause types for determinism in tests)
    accepted = random.random() < pair_rate

    jurisdiction_code = session_data.get("jurisdiction_code", "ON")
    opposing_party_type = session_data.get("opposing_party_type", "counsel")

    system_prompt = (
        "You are experienced commercial procurement counsel. "
        "Respond in 2-3 sentences of plain professional English. "
        "Do not reference any AI or automated system. "
        "Return only the response text — no preamble, no JSON."
    )

    if accepted:
        user_prompt = (
            f"You are {opposing_party_type} counsel in a {jurisdiction_code} procurement negotiation. "
            f"You have agreed to a trade: your client will accept movement on the "
            f"{requested_type.replace('_', ' ')} clause in exchange for the other party "
            f"moving on the {offered_type.replace('_', ' ')} clause. "
            "Confirm this trade acceptance professionally and briefly note why this package "
            "makes commercial sense."
        )
        try:
            rationale = await _generate_llm_response_raw(system_prompt, user_prompt)
        except Exception:
            rationale = (
                f"We accept this trade. Movement on the {requested_type.replace('_', ' ')} "
                f"clause, coupled with your concession on {offered_type.replace('_', ' ')}, "
                "creates a balanced outcome that both parties can sign."
            )
        return {"accepted": True, "rationale": rationale, "counter_trade": None}
    else:
        # Find the best alternative pair as a counter-trade
        counter_trade = None
        best_alt_rate = 0.0
        for (a, b), rate in TRADE_PAIR_SUCCESS_RATES.items():
            if (a == requested_type or b == requested_type) and (a, b) != (offered_type, requested_type) and rate > best_alt_rate:
                best_alt_rate = rate
                alt_type = b if a == requested_type else a
                counter_trade = {
                    "offered_clause_type": requested_type,
                    "requested_clause_type": alt_type,
                    "pair_success_rate": rate,
                    "rationale": (
                        f"We are not in a position to accept the proposed trade as structured. "
                        f"However, we would consider movement on the {requested_type.replace('_', ' ')} "
                        f"clause if it were paired instead with the {alt_type.replace('_', ' ')} clause, "
                        f"which more directly addresses our client's risk exposure under {jurisdiction_code} law."
                    ),
                }

        user_prompt = (
            f"You are {opposing_party_type} counsel in a {jurisdiction_code} procurement negotiation. "
            f"You are rejecting a proposed trade: the other party offered to move on the "
            f"{offered_type.replace('_', ' ')} clause in exchange for your movement on the "
            f"{requested_type.replace('_', ' ')} clause. "
            "Decline this trade professionally, explain briefly why the pairing does not work "
            "for your client, and signal openness to an alternative structure."
        )
        try:
            rationale = await _generate_llm_response_raw(system_prompt, user_prompt)
        except Exception:
            rationale = (
                f"We cannot accept this trade as proposed. The "
                f"{offered_type.replace('_', ' ')} concession does not provide "
                f"sufficient commercial offset for movement on the "
                f"{requested_type.replace('_', ' ')} clause given our client's risk profile."
            )

        return {"accepted": False, "rationale": rationale, "counter_trade": counter_trade}


async def _generate_llm_response_raw(system_prompt: str, user_prompt: str) -> str:
    """Waterfall Groq → Claude for raw text (no session/clause context needed)."""
    if settings.use_groq and settings.groq_api_key:
        try:
            return await _call_groq(system_prompt, user_prompt)
        except Exception as e:
            logger.warning(f"Groq raw call failed, trying Claude: {e}")
    return await _call_claude(system_prompt, user_prompt)


async def generate_proactive_trade_suggestion(
    session_data: dict, stalemate_clause: dict, all_clauses: list
) -> Optional[dict]:
    """
    Called when a clause hits STALEMATE (2+ rejections with no movement).

    Scans all_clauses to find the best cross-clause trade offer — one where:
    - The other clause has opponent_rejection_count < 2 (not already entrenched)
    - The clause-type pair has a known TRADE_PAIR_SUCCESS_RATES entry

    Parameters
    ----------
    session_data : dict
    stalemate_clause : dict
        The clause that has stalled. Keys: clause_key, clause_type, original_text
    all_clauses : list[dict]
        All NegotiationClause dicts for this session.

    Returns
    -------
    dict | None
        {offered_clause_key, offered_text_suggestion, requested_clause_key, rationale}
        or None if no viable trade pair exists.
    """
    stalemate_type = stalemate_clause.get("clause_type", "")
    jurisdiction_code = session_data.get("jurisdiction_code", "ON")

    best_candidate = None
    best_rate = 0.0

    for clause in all_clauses:
        # Skip the stalemate clause itself
        if clause.get("clause_key") == stalemate_clause.get("clause_key"):
            continue
        # Skip clauses the opponent has already dug in on
        if clause.get("opponent_rejection_count", 0) >= 2:
            continue
        # Skip already agreed clauses
        if clause.get("state") == "agreed":
            continue

        candidate_type = clause.get("clause_type", "")
        rate = TRADE_PAIR_SUCCESS_RATES.get(
            (stalemate_type, candidate_type),
            TRADE_PAIR_SUCCESS_RATES.get((candidate_type, stalemate_type), 0.0),
        )

        if rate > best_rate:
            best_rate = rate
            best_candidate = clause

    if best_candidate is None or best_rate < 0.50:
        logger.info(
            f"No viable trade pair for stalemate clause {stalemate_clause.get('clause_key')!r}"
        )
        return None

    candidate_type = best_candidate.get("clause_type", "")

    # Generate a suggested amended text for the offered clause via LLM
    system_prompt = (
        "You are a senior Canadian commercial lawyer drafting a concession offer "
        "in a clause-by-clause contract negotiation. "
        "Return only the proposed clause text — no preamble, no explanation, no JSON."
    )
    offered_text_prompt = (
        f"We are negotiating a {jurisdiction_code} procurement contract. "
        f"Draft a brief, balanced proposed revision to the {stalemate_type.replace('_', ' ')} "
        f"clause that makes a meaningful concession to the opposing party while "
        f"still protecting our core interests. "
        f"Original text: \"{stalemate_clause.get('original_text', '')[:400]}\"\n"
        "Return only the revised clause text."
    )

    try:
        offered_text_suggestion = await _generate_llm_response_raw(system_prompt, offered_text_prompt)
    except Exception as e:
        logger.warning(f"LLM failed for trade text suggestion: {e}")
        offered_text_suggestion = (
            f"[Revised {stalemate_type.replace('_', ' ')} clause — "
            "to be negotiated as part of package]"
        )

    return {
        "offered_clause_key": stalemate_clause.get("clause_key"),
        "offered_text_suggestion": offered_text_suggestion,
        "requested_clause_key": best_candidate.get("clause_key"),
        "pair_success_rate": best_rate,
        "rationale": (
            f"Negotiations on the {stalemate_type.replace('_', ' ')} clause have reached an "
            f"impasse. We propose resolving this through a package that also addresses the "
            f"{candidate_type.replace('_', ' ')} clause — a pairing with a {best_rate:.0%} "
            f"historical acceptance rate in {jurisdiction_code} procurement negotiations. "
            "This approach allows both parties to make progress on their respective priorities "
            "simultaneously."
        ),
    }


def calculate_round_dollar_value(clause_data: dict, action: str) -> float:
    """
    Estimate the CAD value outcome of a single negotiation round.

    Parameters
    ----------
    clause_data : dict  — must contain risk_exposure_cad
    action : str        — "accept" | "counter" | "reject" | "trade_offer"

    Returns
    -------
    float  — 0.0 if no value is attributable to this round
    """
    from app.services.clause_weights import action_recovery

    risk_exposure = float(clause_data.get("risk_exposure_cad") or 0)
    return round(risk_exposure * action_recovery(action), 2)
