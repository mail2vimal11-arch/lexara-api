"""Extract a temporal_spec from an obligation sentence.

Pattern-based first-pass extractor. Returns a dict shaped like
obligation_temporal_specs (sans spec_id / obligation_id — caller fills those).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

# spaCy imports are deferred to _ensure_loaded() so this module can be imported
# (and its `extract_temporal_spec` monkeypatched) in test envs that don't have
# spaCy or the language model installed.
_nlp: Any | None = None
_matcher: Any | None = None


def _ensure_loaded() -> tuple[Any, Any]:
    global _nlp, _matcher
    if _nlp is None:
        import spacy
        from spacy.matcher import Matcher
        _nlp = spacy.load("en_core_web_lg")
        _matcher = Matcher(_nlp.vocab)
        for label, pattern in _PATTERNS:
            _matcher.add(label, [pattern])
    assert _matcher is not None
    return _nlp, _matcher


_PATTERNS: list[tuple[str, list[dict]]] = [
    ("REL_WITHIN", [
        {"LOWER": "within"},
        {"LIKE_NUM": True},
        {"LOWER": {"IN": ["calendar", "business", "working"]}, "OP": "?"},
        {"LOWER": {"IN": ["day", "days", "week", "weeks", "month", "months"]}},
        {"LOWER": {"IN": ["of", "after", "from", "following"]}},
    ]),
    ("REL_PRIOR", [
        {"LIKE_NUM": True},
        {"LOWER": {"IN": ["calendar", "business", "working"]}, "OP": "?"},
        {"LOWER": {"IN": ["day", "days", "week", "weeks", "month", "months"]}},
        {"LOWER": {"IN": ["before", "prior"]}},
        {"LOWER": "to", "OP": "?"},
    ]),
    ("ABS_BY", [
        {"LOWER": {"IN": ["by", "before", "on"]}},
        {"LOWER": "or", "OP": "?"},
        {"LOWER": {"IN": ["before", "after"]}, "OP": "?"},
        {"ENT_TYPE": "DATE"},
    ]),
    ("REL_UPON", [
        {"LOWER": {"IN": ["upon", "on"]}},
        {"POS": {"IN": ["NOUN", "PROPN", "DET"]}, "OP": "+"},
    ]),
]


ANCHOR_LEXICON: dict[str, list[str]] = {
    "contract_award":  ["contract award", "award of contract", "award date", "date of award"],
    "effective_date":  ["effective date", "commencement date", "contract effective date"],
    "go_live":         ["go-live", "go live", "production launch", "cutover"],
    "acceptance":      ["acceptance", "final acceptance", "deliverable acceptance"],
    "execution":       ["execution of this agreement", "signing of this agreement"],
}


def resolve_anchor_phrase(phrase: str) -> str | None:
    p = phrase.lower().strip()
    for key, aliases in ANCHOR_LEXICON.items():
        if any(a in p for a in aliases):
            return key
    return None


_UNIT_MAP = {
    "calendar day":  "calendar_days", "calendar days":  "calendar_days",
    "business day":  "business_days", "business days":  "business_days",
    "working day":   "business_days", "working days":   "business_days",
    "day":           "calendar_days", "days":           "calendar_days",
    "week":          "weeks",         "weeks":          "weeks",
    "month":         "months",        "months":         "months",
}


def extract_temporal_spec(obligation_text: str) -> dict:
    nlp, matcher = _ensure_loaded()
    doc = nlp(obligation_text)
    matches = matcher(doc)

    if not matches:
        return _none_spec()

    matches.sort(key=lambda m: m[1])
    match_id, start, end = matches[0]
    label = nlp.vocab.strings[match_id]
    span = doc[start:end]

    if label == "ABS_BY":
        date_token = next((t for t in span if t.ent_type_ == "DATE"), None)
        date_text = None
        if date_token is not None:
            for ent in doc.ents:
                if ent.label_ == "DATE" and date_token in ent:
                    date_text = ent.text
                    break
        parsed = _parse_date(date_text)
        return {
            "kind": "absolute",
            "absolute_date": parsed,
            "raw_phrase": span.text,
            "confidence": 0.9 if parsed else 0.4,
            "anchor_key": None,
            "anchor_obligation_id": None,
            "offset_value": None,
            "offset_unit": None,
            "direction": None,
            "recurrence_rule": None,
        }

    if label in ("REL_WITHIN", "REL_PRIOR"):
        offset_value = _extract_number(span)
        offset_unit  = _extract_unit(span.text)
        direction    = "before" if label == "REL_PRIOR" else "after"
        anchor_text  = doc[end:end + 8].text
        anchor_key   = resolve_anchor_phrase(anchor_text)
        confidence   = 0.85 if (offset_value and anchor_key) else 0.5

        return {
            "kind": "relative",
            "absolute_date": None,
            "offset_value": offset_value,
            "offset_unit": offset_unit,
            "direction": direction,
            "anchor_key": anchor_key,
            "anchor_obligation_id": None,
            "raw_phrase": doc[start:min(len(doc), end + 8)].text,
            "confidence": confidence,
            "recurrence_rule": None,
        }

    if label == "REL_UPON":
        anchor_text = doc[start + 1:end].text
        anchor_key  = resolve_anchor_phrase(anchor_text)
        return {
            "kind": "relative",
            "absolute_date": None,
            "offset_value": 0,
            "offset_unit": "calendar_days",
            "direction": "on",
            "anchor_key": anchor_key,
            "anchor_obligation_id": None,
            "raw_phrase": span.text,
            "confidence": 0.7 if anchor_key else 0.4,
            "recurrence_rule": None,
        }

    return _none_spec()


def _extract_number(span):
    for tok in span:
        if tok.like_num:
            try:
                return int(float(tok.text))
            except ValueError:
                return None
    return None


def _extract_unit(text: str) -> str:
    t = text.lower()
    for k in sorted(_UNIT_MAP, key=len, reverse=True):
        if k in t:
            return _UNIT_MAP[k]
    return "calendar_days"


_DATE_FORMATS = (
    "%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y",
    "%Y-%m-%d", "%d %B %Y", "%d %b %Y",
)


def _parse_date(text):
    if not text:
        return None
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _none_spec():
    return {
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
