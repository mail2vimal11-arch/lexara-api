"""
NLP Pipeline — clause extraction, classification, risk detection, and improvement.
Uses spaCy for sentence segmentation + rule-based + ML classifier.
"""

from __future__ import annotations
import re
import logging
from typing import Optional

import spacy

logger = logging.getLogger(__name__)

# Load spaCy model (downloaded at Docker build time)
try:
    _nlp = spacy.load("en_core_web_sm")
except OSError:
    _nlp = None
    logger.warning("spaCy model not found. Sentence extraction will fall back to regex.")


# ── Clause Extraction ─────────────────────────────────────────────────────────

def extract_clauses(text: str) -> list[str]:
    """
    Segment text into individual clauses using spaCy sentence tokenization.
    Falls back to period-split if model unavailable.
    Filters out very short fragments (< 20 chars).
    """
    if _nlp:
        doc = _nlp(text[:100_000])  # cap for performance
        return [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 20]
    # Fallback: split on sentence-ending punctuation
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]


# ── Clause Classification ─────────────────────────────────────────────────────

# Keyword rules ordered by specificity — first match wins
_CLASSIFICATION_RULES: list[tuple[list[str], str]] = [
    (["shall deliver", "must deliver", "will deliver", "deliverable", "output", "report shall"], "Deliverables"),
    (["within", "no later than", "by the date", "completion date", "milestone", "deadline"], "Timeline_Milestones"),
    (["shall be paid", "payment upon", "invoice", "fee", "compensation", "net 30", "net30"], "Commercial_Terms"),
    (["uptime", "sla", "service level", "kpi", "performance standard", "response time", "99."], "Performance_Standards"),
    (["shall provide", "shall perform", "managed service", "consulting", "advisory", "professional service"], "Services"),
    (["pipeda", "privacy act", "aoda", "accessibility", "gdpr", "security standard", "compliance", "regulation"], "Compliance_Regulatory"),
    (["indemnif", "liability", "hold harmless", "insurance"], "Risk_Allocation"),
    (["termination", "terminate", "cancellation", "default"], "Termination"),
    (["change request", "scope change", "variation", "amendment", "modification"], "Change_Management"),
    (["acceptance", "sign-off", "testing", "validation", "approval of deliverable"], "Acceptance_Closure"),
    (["confidential", "non-disclosure", "nda", "proprietary"], "Confidentiality"),
    (["intellectual property", "ip ownership", "copyright", "patent", "licence"], "Intellectual_Property"),
    (["governing law", "jurisdiction", "dispute", "arbitration"], "Governance"),
]


def classify_clause(text: str) -> str:
    """
    Classify a clause into an SOW ontology category using keyword rules.
    Returns 'General' if no rule matches.
    """
    lower = text.lower()
    for keywords, label in _CLASSIFICATION_RULES:
        if any(kw in lower for kw in keywords):
            return label
    return "General"


# ── Risk Detection ────────────────────────────────────────────────────────────

_RISK_PATTERNS: dict[str, list[str]] = {
    "High": [
        "reasonable efforts", "reasonable endeavours", "best efforts",
        "as needed", "as required", "etc.", "and/or", "as soon as possible",
        "timely manner", "appropriate", "suitable", "at its discretion",
    ],
    "Medium": [
        "best endeavours", "commercially reasonable", "may be required",
        "subject to change", "approximate", "estimated",
    ],
}


def detect_risk(text: str) -> str:
    """
    Detect ambiguous or high-risk language in a clause.
    Returns 'High', 'Medium', or 'Low'.
    """
    lower = text.lower()
    for level, patterns in _RISK_PATTERNS.items():
        if any(p in lower for p in patterns):
            return level
    return "Low"


# ── Clause Improvement ────────────────────────────────────────────────────────

_IMPROVEMENTS: list[tuple[str, str]] = [
    ("as soon as possible",            "within 5 business days"),
    ("in a timely manner",             "within the agreed timeline"),
    ("reasonable efforts",             "commercially reasonable efforts, with a minimum standard of [specify]"),
    ("best efforts",                   "commercially reasonable efforts"),
    ("and/or",                         "and"),     # legal drafting avoids and/or
    ("etc.",                           "[list all items explicitly]"),
    ("as needed",                      "as specified in Schedule A"),
    ("at its discretion",              "acting reasonably"),
    ("appropriate",                    "[specify the applicable standard]"),
]


def improve_clause(text: str) -> str:
    """
    Apply plain-language improvements to a clause.
    Replaces known ambiguous phrases with stronger, measurable language.
    """
    improved = text
    for vague, better in _IMPROVEMENTS:
        improved = re.sub(re.escape(vague), better, improved, flags=re.IGNORECASE)
    return improved


# ── Combined Analysis ─────────────────────────────────────────────────────────

def analyze_clause(text: str) -> dict:
    """
    Run full analysis pipeline on a single clause.
    Returns type, risk level, improved text, and confidence.
    """
    clause_type = classify_clause(text)
    risk = detect_risk(text)
    improved = improve_clause(text)
    return {
        "clause_type": clause_type,
        "risk_level": risk,
        "improved": improved if improved != text else None,
        "confidence_score": 0.85 if clause_type != "General" else 0.4,
    }
