"""
Obligation Extractor — turns drafted SOW text into structured obligation
proposals using the existing LLM stack.

This service NEVER writes to the database. It returns a list of dicts that
match the shape of `ObligationCreate` so the caller (a portfolio route) can
either present them to the user for review or persist them via the existing
batch-create endpoint after explicit user approval.

The extraction flow:
  1. Build a strict-JSON prompt that enumerates the allowed obligation_type
     and party enums plus a few-shot examples.
  2. Call the existing async LLM helper (analyze_with_claude) — same fallback
     chain (Groq -> HF -> Claude) that workbench_service.generate_section_guidance
     uses today.
  3. Parse the JSON defensively. The LLM is allowed to wrap JSON in prose; we
     locate the JSON block and parse it. On any parse failure we return [] and
     log a warning rather than raising.
  4. Validate each entry against the schema constraints. Drop entries with
     unknown obligation_type / party or with a missing description.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Allowed enum values — kept in sync with app/models/obligation.py
# ---------------------------------------------------------------------------

ALLOWED_OBLIGATION_TYPES = {
    "payment",
    "delivery",
    "sla",
    "data_handling",
    "reporting",
    "renewal",
    "termination_notice",
    "indemnity",
    "other",
}

ALLOWED_PARTIES = {"us", "counterparty"}

ALLOWED_CONFIDENCE = {"high", "medium", "low"}

# Fields the user is allowed to fill on an obligation. Anything else returned
# by the LLM is dropped before the proposal is returned to the caller.
USER_FILLABLE_FIELDS = {
    "obligation_type",
    "party",
    "description",
    "deadline_days_from_trigger",
    "trigger_event",
    "absolute_deadline",
    "penalty_formula",
    "penalty_amount_cad",
    "liability_cap_cad",
    "source_clause_text",
    "source_clause_key",
    "metadata_json",
}


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

OBLIGATION_EXTRACTION_SYSTEM_PROMPT = """You are a Canadian contract analyst. Your job is to read drafted Statement of Work (SOW) or contract text and extract every binding obligation as a structured JSON list. Every obligation you return must answer four questions: WHO owes the duty, WHAT they must do, WHEN it is triggered/due, and WHAT THE CONSEQUENCE is if they miss it.

Return ONLY a JSON array. Do not wrap it in prose. Do not add commentary outside the JSON. The array must be a JSON list (possibly empty).

Each element of the array must be a JSON object with these fields:

  obligation_type   REQUIRED. One of EXACTLY these strings:
                    "payment", "delivery", "sla", "data_handling",
                    "reporting", "renewal", "termination_notice",
                    "indemnity", "other".
                    Use "other" only when none of the above fit.

  party             REQUIRED. EXACTLY one of: "us", "counterparty".
                    "us" = the buyer / our side / the procuring entity.
                    "counterparty" = the vendor / contractor / supplier.

  description       REQUIRED. One sentence in plain English describing
                    the duty. Example: "Pay vendor invoices within 60 days
                    of receipt."

  deadline_days_from_trigger
                    OPTIONAL. Integer number of days from the trigger
                    event, or null if not applicable. NEVER a string.
                    Example: 60.

  trigger_event     OPTIONAL. Short snake_case label naming the event
                    that starts the deadline clock, or null. Examples:
                    "invoice_received", "go_live", "contract_signature",
                    "incident_reported".

  absolute_deadline OPTIONAL. ISO-8601 date string (YYYY-MM-DD) when the
                    deadline is a fixed calendar date, or null.

  penalty_formula   OPTIONAL. Free text describing the penalty if the
                    obligation is missed, or null. Example:
                    "1.5% of contract value per day late".

  penalty_amount_cad OPTIONAL. Number (CAD) when a fixed penalty applies,
                    else null.

  liability_cap_cad OPTIONAL. Number (CAD) for any cap that limits the
                    party's exposure on this obligation, else null.

  source_clause_text REQUIRED WHEN POSSIBLE. The exact sentence (or
                    short fragment) from the input that you derived this
                    obligation from. Verbatim. This is how the user
                    audits the extraction.

  _extraction_confidence  OPTIONAL. One of "high", "medium", "low" — your
                    confidence that this obligation is correctly extracted
                    from the source text.

EXAMPLES

Input sentence: "Vendor shall pay invoices within 60 days of receipt."
Output element:
  {
    "obligation_type": "payment",
    "party": "us",
    "description": "Pay vendor invoices within 60 days of receipt.",
    "deadline_days_from_trigger": 60,
    "trigger_event": "invoice_received",
    "absolute_deadline": null,
    "penalty_formula": null,
    "penalty_amount_cad": null,
    "liability_cap_cad": null,
    "source_clause_text": "Vendor shall pay invoices within 60 days of receipt.",
    "_extraction_confidence": "high"
  }

Input sentence: "The Contractor shall deliver the migrated system within 90 days of contract signature, or pay liquidated damages of $5,000 per day of delay up to a cap of $250,000."
Output element:
  {
    "obligation_type": "delivery",
    "party": "counterparty",
    "description": "Deliver the migrated system within 90 days of contract signature.",
    "deadline_days_from_trigger": 90,
    "trigger_event": "contract_signature",
    "absolute_deadline": null,
    "penalty_formula": "$5,000 per day of delay",
    "penalty_amount_cad": 5000,
    "liability_cap_cad": 250000,
    "source_clause_text": "The Contractor shall deliver the migrated system within 90 days of contract signature, or pay liquidated damages of $5,000 per day of delay up to a cap of $250,000.",
    "_extraction_confidence": "high"
  }

Input sentence: "The Contractor shall maintain 99.9% uptime measured monthly; service credits of 5% of monthly fees apply if uptime falls below 99.5%."
Output element:
  {
    "obligation_type": "sla",
    "party": "counterparty",
    "description": "Maintain 99.9% monthly uptime.",
    "deadline_days_from_trigger": null,
    "trigger_event": "monthly_measurement",
    "absolute_deadline": null,
    "penalty_formula": "5% of monthly fees if uptime < 99.5%",
    "penalty_amount_cad": null,
    "liability_cap_cad": null,
    "source_clause_text": "The Contractor shall maintain 99.9% uptime measured monthly; service credits of 5% of monthly fees apply if uptime falls below 99.5%.",
    "_extraction_confidence": "high"
  }

If the input contains no obligations, return: []
"""


def _build_user_prompt(
    sow_text: str,
    contract_type: Optional[str],
    contract_value_cad: Optional[float],
    jurisdiction_code: Optional[str],
) -> str:
    ctx_lines = []
    if contract_type:
        ctx_lines.append(f"  contract_type: {contract_type}")
    if contract_value_cad is not None:
        ctx_lines.append(f"  contract_value_cad: {contract_value_cad}")
    if jurisdiction_code:
        ctx_lines.append(f"  jurisdiction_code: {jurisdiction_code}")
    ctx_block = "\n".join(ctx_lines) if ctx_lines else "  (none provided)"

    # Truncate aggressively so we never blow the model context. SOWs are long
    # but the LLM only needs enough to extract obligation sentences.
    truncated = (sow_text or "")[:8000]

    return (
        f"{OBLIGATION_EXTRACTION_SYSTEM_PROMPT}\n\n"
        f"CONTRACT CONTEXT\n{ctx_block}\n\n"
        f"SOW / CONTRACT TEXT (up to 8000 chars):\n"
        f"\"\"\"\n{truncated}\n\"\"\"\n\n"
        f"Return ONLY a JSON array of obligation objects."
    )


# ---------------------------------------------------------------------------
# Defensive JSON parsing
# ---------------------------------------------------------------------------

def _extract_json_array(raw: Any) -> Optional[List[Any]]:
    """Locate and parse a JSON array out of an LLM response.

    The LLM helper may return either a parsed dict (if it auto-parsed) or a
    string. It can also wrap the JSON list in prose, markdown fences, or even
    inside a dict under various keys. We try each shape defensively and return
    None if nothing parses.
    """
    if raw is None:
        return None

    # Case A: helper already parsed the LLM output into a dict. Look for the
    # list under common keys.
    if isinstance(raw, dict):
        for key in ("obligations", "proposals", "items", "results", "data"):
            v = raw.get(key)
            if isinstance(v, list):
                return v
        # Nothing list-shaped in the dict.
        return None

    # Case B: a list came back directly.
    if isinstance(raw, list):
        return raw

    # Case C: a string. Strip code fences and locate the array boundaries.
    if isinstance(raw, str):
        text = raw.strip()
        # Strip ```json ... ``` or ``` ... ``` fences.
        if "```" in text:
            # Take whatever's between the first fence pair.
            m = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
            if m:
                text = m.group(1).strip()

        # Find the first '[' and the matching last ']'.
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Last ditch: try parsing the whole string.
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return _extract_json_array(parsed)
        except json.JSONDecodeError:
            return None

    return None


# ---------------------------------------------------------------------------
# Per-entry validation
# ---------------------------------------------------------------------------

def _coerce_int(value: Any) -> Optional[int]:
    """Best-effort int coercion. Returns None on failure."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None  # don't let `True` become `1`
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            return None
    return None


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Strip $ and commas commonly emitted by LLMs.
        cleaned = value.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    return None


def _validate_and_clean(raw_entry: Any) -> Optional[Dict[str, Any]]:
    """Validate a single LLM-emitted obligation dict.

    Returns a sanitized dict shaped like ObligationCreate (plus optional
    _extraction_confidence) or None if the entry is unusable.
    """
    if not isinstance(raw_entry, dict):
        return None

    obligation_type = raw_entry.get("obligation_type")
    party = raw_entry.get("party")
    description = raw_entry.get("description")

    # Hard requirements
    if not isinstance(obligation_type, str) or obligation_type not in ALLOWED_OBLIGATION_TYPES:
        return None
    if not isinstance(party, str) or party not in ALLOWED_PARTIES:
        return None
    if not isinstance(description, str) or not description.strip():
        return None

    cleaned: Dict[str, Any] = {
        "obligation_type": obligation_type,
        "party": party,
        "description": description.strip(),
    }

    # Optional integer/float/string passthroughs with light coercion.
    days = _coerce_int(raw_entry.get("deadline_days_from_trigger"))
    if days is not None:
        cleaned["deadline_days_from_trigger"] = days

    trigger = raw_entry.get("trigger_event")
    if isinstance(trigger, str) and trigger.strip():
        cleaned["trigger_event"] = trigger.strip()

    abs_dl = raw_entry.get("absolute_deadline")
    if isinstance(abs_dl, str) and abs_dl.strip():
        # Light shape check — Pydantic on the route side will reject malformed
        # date strings. Accept what looks like ISO YYYY-MM-DD.
        if re.match(r"^\d{4}-\d{2}-\d{2}$", abs_dl.strip()):
            cleaned["absolute_deadline"] = abs_dl.strip()

    pf = raw_entry.get("penalty_formula")
    if isinstance(pf, str) and pf.strip():
        cleaned["penalty_formula"] = pf.strip()

    pa = _coerce_float(raw_entry.get("penalty_amount_cad"))
    if pa is not None:
        cleaned["penalty_amount_cad"] = pa

    lc = _coerce_float(raw_entry.get("liability_cap_cad"))
    if lc is not None:
        cleaned["liability_cap_cad"] = lc

    sct = raw_entry.get("source_clause_text")
    if isinstance(sct, str) and sct.strip():
        cleaned["source_clause_text"] = sct.strip()

    sck = raw_entry.get("source_clause_key")
    if isinstance(sck, str) and sck.strip():
        cleaned["source_clause_key"] = sck.strip()

    md = raw_entry.get("metadata_json")
    if isinstance(md, dict):
        cleaned["metadata_json"] = md

    # Extraction confidence is a UI-only hint — preserve it but only if valid.
    conf = raw_entry.get("_extraction_confidence")
    if isinstance(conf, str) and conf.lower() in ALLOWED_CONFIDENCE:
        cleaned["_extraction_confidence"] = conf.lower()

    return cleaned


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def extract_obligations_from_text(
    sow_text: str,
    contract_type: Optional[str] = None,
    contract_value_cad: Optional[float] = None,
    jurisdiction_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Extract a list of proposed obligations from drafted SOW text.

    The returned dicts are shaped to match the `ObligationCreate` Pydantic
    schema (plus an optional `_extraction_confidence` UI hint). They are NOT
    persisted — the caller is responsible for surfacing them to the user for
    review and then calling the batch-create endpoint to commit approved
    proposals.

    On any LLM or parsing failure this function returns an empty list and
    logs a warning. It never raises — extraction is opportunistic.
    """
    if not sow_text or not sow_text.strip():
        return []

    # Lazy import to keep this module decoupled from the LLM module at import
    # time (and to make monkey-patching simpler in tests).
    from app.services.llm_service import analyze_with_claude

    prompt = _build_user_prompt(
        sow_text=sow_text,
        contract_type=contract_type,
        contract_value_cad=contract_value_cad,
        jurisdiction_code=jurisdiction_code,
    )

    raw_response: Any = None
    try:
        raw_response = await analyze_with_claude(
            text=prompt,
            contract_type=contract_type or "auto",
            jurisdiction=jurisdiction_code or "ON",
            mode="obligation_extraction",
        )
    except Exception as exc:
        logger.warning("Obligation extraction LLM call failed: %s", exc)
        return []

    # The response may be: a list, a dict with a "raw" string, a dict with
    # an "obligations" list, or a string. _extract_json_array handles all.
    parsed = _extract_json_array(raw_response)

    # If the helper returned a dict that wasn't shaped like {obligations: [...]}
    # try peeking at common stringy keys.
    if parsed is None and isinstance(raw_response, dict):
        for key in ("raw", "text", "content", "completion"):
            v = raw_response.get(key)
            if isinstance(v, str):
                parsed = _extract_json_array(v)
                if parsed is not None:
                    break

    if parsed is None:
        logger.warning(
            "Obligation extraction: could not locate JSON array in LLM response. "
            "type=%s preview=%r",
            type(raw_response).__name__,
            (str(raw_response)[:200] if raw_response is not None else None),
        )
        return []

    proposals: List[Dict[str, Any]] = []
    for entry in parsed:
        cleaned = _validate_and_clean(entry)
        if cleaned is not None:
            proposals.append(cleaned)
        else:
            logger.debug("Dropping malformed extraction entry: %r", entry)

    return proposals
