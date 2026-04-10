"""
linter.py — Justice Canada Readability Linter
Flags legalese, passive voice, plural bidder/contractor terms,
and non-gender-neutral language per the DoJ Guide to Readability.
"""

import re
import spacy

# Load spaCy English model (small; run `python -m spacy download en_core_web_sm` first)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None  # Graceful degradation if model not installed


# ── 1. Archaic Legalese ─────────────────────────────────────────────────────

# These terms are flagged with plain-English suggestions.
LEGALESE_MAP = {
    r"\bhereinbefore\b": "above / previously in this document",
    r"\bhereinafter\b": "below / from this point on (or just use the defined term)",
    r"\bwitnesseth\b": "[remove — use a plain recitals heading]",
    r"\bwhereas\b": "Background / Recitals",
    r"\bhereby\b": "[remove — rephrase the sentence]",
    r"\bherein\b": "in this document / in this agreement",
    r"\bhereof\b": "of this agreement",
    r"\bhereunder\b": "under this agreement",
    r"\bthereof\b": "of that",
    r"\btherein\b": "in that",
    r"\bthereunder\b": "under that",
    r"\bwhereof\b": "of which",
    r"\bwherein\b": "in which",
    r"\bforthwith\b": "immediately",
    r"\bnotwithstanding\b": "despite / even if",
    r"\bin witness whereof\b": "[use a plain signature block heading]",
    r"\bpursuant to\b": "under / in accordance with",
    r"\binter alia\b": "among other things",
    r"\bmutatis mutandis\b": "with necessary changes",
    r"\bpari passu\b": "equally / at the same rate",
    r"\bforce majeure\b": "unforeseeable event beyond a party's control (define explicitly)",
    r"\btime is of the essence\b": "deadlines in this agreement are strict and must be met",
}


def flag_legalese(text: str) -> list[dict]:
    """
    Scan text for archaic legalese terms.
    Returns a list of findings: {term, start, end, suggestion, sentence}.
    """
    findings = []
    for pattern, suggestion in LEGALESE_MAP.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Extract surrounding sentence for context
            sentence_start = text.rfind("\n", 0, match.start()) + 1
            sentence_end = text.find("\n", match.end())
            sentence = text[sentence_start: sentence_end if sentence_end != -1 else len(text)].strip()
            findings.append({
                "type": "legalese",
                "term": match.group(),
                "start": match.start(),
                "end": match.end(),
                "suggestion": suggestion,
                "context": sentence[:200],
            })
    return findings


# ── 2. Passive Voice Detection ───────────────────────────────────────────────

# Passive voice pattern: auxiliary verb (to be) + past participle
# e.g. "is required", "shall be provided", "was determined", "are expected"
PASSIVE_PATTERN = re.compile(
    r"\b(is|are|was|were|be|been|being|shall be|will be|must be|should be|may be|can be)"
    r"\s+(\w+ed|awarded|done|given|made|paid|provided|required|sent|shown|taken|used|written)\b",
    re.IGNORECASE,
)

# Active voice procurement verbs for suggestions
ACTIVE_SUGGESTIONS = {
    "is required": "The Contractor shall",
    "are required": "The Contractor shall",
    "shall be provided": "The Contractor shall provide",
    "shall be submitted": "The Bidder shall submit",
    "must be submitted": "The Bidder must submit",
    "is expected": "The Contractor is expected to",
    "will be evaluated": "Canada will evaluate",
    "will be reviewed": "Canada will review",
}


def flag_passive_voice(text: str) -> list[dict]:
    """
    Detect passive voice constructions.
    Uses regex for common procurement patterns + optional spaCy dep parsing.
    """
    findings = []

    # Regex pass — catches most common procurement passive constructions
    for match in PASSIVE_PATTERN.finditer(text):
        phrase = match.group().lower()
        suggestion = ACTIVE_SUGGESTIONS.get(phrase, "Rewrite using active voice (e.g., 'The Contractor shall...')")
        sentence_start = text.rfind(".", 0, match.start()) + 1
        sentence_end = text.find(".", match.end()) + 1
        context = text[sentence_start:sentence_end].strip()
        findings.append({
            "type": "passive_voice",
            "term": match.group(),
            "start": match.start(),
            "end": match.end(),
            "suggestion": suggestion,
            "context": context[:200],
        })

    # spaCy dependency parse pass (more precise, catches irregular past participles)
    if nlp:
        doc = nlp(text[:50000])  # cap for performance
        for token in doc:
            # nsubjpass = nominal subject of passive, auxpass = passive auxiliary
            if token.dep_ == "nsubjpass":
                sent_text = token.sent.text.strip()
                findings.append({
                    "type": "passive_voice",
                    "term": token.sent.text.strip()[:80],
                    "start": token.sent.start_char,
                    "end": token.sent.end_char,
                    "suggestion": "Rewrite using active voice (e.g., 'The Contractor shall...')",
                    "context": sent_text[:200],
                })

    # Deduplicate by start position
    seen = set()
    unique = []
    for f in findings:
        if f["start"] not in seen:
            seen.add(f["start"])
            unique.append(f)
    return unique


# ── 3. Plural Bidder/Contractor Terms ────────────────────────────────────────

# Plural terms create ambiguity in procurement docs.
# "Bidders must" → "The Bidder must"  /  "Contractors shall" → "The Contractor shall"
PLURAL_PARTY_PATTERN = re.compile(
    r"\b(Bidders?|Contractors?|Proponents?|Vendors?|Suppliers?|Respondents?)"
    r"\s+(must|shall|should|will|are|may|have|need)\b",
)

SINGULAR_MAP = {
    "Bidders": "The Bidder",
    "Contractors": "The Contractor",
    "Proponents": "The Proponent",
    "Vendors": "The Vendor",
    "Suppliers": "The Supplier",
    "Respondents": "The Respondent",
}


def flag_plural_parties(text: str) -> list[dict]:
    """
    Flag plural party references and suggest singular replacements.
    """
    findings = []
    for match in PLURAL_PARTY_PATTERN.finditer(text):
        term = match.group(1)
        verb = match.group(2)
        singular = SINGULAR_MAP.get(term, f"The {term.rstrip('s')}")
        findings.append({
            "type": "plural_party",
            "term": match.group(),
            "start": match.start(),
            "end": match.end(),
            "suggestion": f'Use "{singular} {verb}" instead of "{term} {verb}"',
            "context": match.group(),
        })
    return findings


# ── 4. Gender-Neutral Language ───────────────────────────────────────────────

# Flag gendered pronouns and titles; suggest neutral alternatives.
GENDERED_MAP = {
    r"\bhe\b": "they",
    r"\bshe\b": "they",
    r"\bhim\b": "them",
    r"\bher\b": "them / their",
    r"\bhis\b": "their",
    r"\bhers\b": "theirs",
    r"\bhimself\b": "themselves",
    r"\bherself\b": "themselves",
    r"\bhe or she\b": "they",
    r"\bhis or her\b": "their",
    r"\bhim or her\b": "them",
    r"\bmanpower\b": "workforce / personnel",
    r"\bmanmade\b": "artificial / manufactured",
    r"\bworkman\b": "worker",
    r"\bchairman\b": "chair / chairperson",
    r"\bsalesman\b": "sales representative",
    r"\bforefathers\b": "ancestors / predecessors",
}


def flag_gendered_language(text: str) -> list[dict]:
    """
    Flag gendered pronouns and titles.
    """
    findings = []
    for pattern, suggestion in GENDERED_MAP.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            sentence_start = text.rfind(".", 0, match.start()) + 1
            sentence_end = text.find(".", match.end()) + 1
            context = text[sentence_start:sentence_end].strip()
            findings.append({
                "type": "gendered_language",
                "term": match.group(),
                "start": match.start(),
                "end": match.end(),
                "suggestion": f'Replace "{match.group()}" with "{suggestion}"',
                "context": context[:200],
            })
    return findings


# ── 5. Master Lint Function ──────────────────────────────────────────────────

def lint(text: str) -> dict:
    """
    Run all linting checks and return a consolidated report.
    """
    return {
        "legalese": flag_legalese(text),
        "passive_voice": flag_passive_voice(text),
        "plural_parties": flag_plural_parties(text),
        "gendered_language": flag_gendered_language(text),
    }
