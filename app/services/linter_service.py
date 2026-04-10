"""
linter_service.py — Justice Canada Readability Linter
Flags AND rewrites: legalese, passive voice, plural party terms, gendered language.
Each finding includes a `revised` field with the actual corrected sentence.
"""

import re
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_sentence(text: str, start: int, end: int) -> tuple[int, int, str]:
    """Extract the full sentence containing the match."""
    # Walk back to sentence start (. or \n)
    s = max(text.rfind(".", 0, start), text.rfind("\n", 0, start)) + 1
    # Walk forward to sentence end
    e_dot = text.find(".", end)
    e_nl  = text.find("\n", end)
    if e_dot == -1 and e_nl == -1:
        e = len(text)
    elif e_dot == -1:
        e = e_nl
    elif e_nl == -1:
        e = e_dot + 1
    else:
        e = min(e_dot, e_nl) + 1
    return s, e, text[s:e].strip()


# ── 1. Archaic Legalese ───────────────────────────────────────────────────────

# Maps regex → plain replacement word/phrase (used for both suggestion and rewrite)
LEGALESE_MAP = {
    r"\bhereinbefore\b":        "above",
    r"\bhereinafter\b":         "below",
    r"\bwitnesseth\b":          "",           # removed entirely
    r"\bwhereas\b":             "Background:",
    r"\bhereby\b":              "",
    r"\bherein\b":              "in this Agreement",
    r"\bhereof\b":              "of this Agreement",
    r"\bhereunder\b":           "under this Agreement",
    r"\bthereof\b":             "of that",
    r"\btherein\b":             "in that",
    r"\bthereunder\b":          "under that",
    r"\bwhereof\b":             "of which",
    r"\bwherein\b":             "in which",
    r"\bforthwith\b":           "immediately",
    r"\bnotwithstanding\b":     "Despite",
    r"\bin witness whereof\b":  "Signed",
    r"\bpursuant to\b":         "under",
    r"\binter alia\b":          "among other things",
    r"\bmutatis mutandis\b":    "with necessary changes",
    r"\bpari passu\b":          "equally",
    r"\bforce majeure\b":       "unforeseeable event beyond a party's control",
    r"\btime is of the essence\b": "all deadlines in this Agreement are strict",
}

LEGALESE_HUMAN = {
    r"\bhereinbefore\b":        'Replace with "above" or reference the specific section',
    r"\bhereinafter\b":         'Replace with "below" or simply use the defined term directly',
    r"\bwitnesseth\b":          "Remove — use a plain 'Recitals' or 'Background' heading",
    r"\bwhereas\b":             'Replace with "Background:" as a section heading',
    r"\bhereby\b":              "Remove and rephrase the sentence in plain language",
    r"\bherein\b":              'Replace with "in this Agreement"',
    r"\bhereof\b":              'Replace with "of this Agreement"',
    r"\bhereunder\b":           'Replace with "under this Agreement"',
    r"\bthereof\b":             'Replace with "of that" or name the specific item',
    r"\btherein\b":             'Replace with "in that" or name the specific document',
    r"\bthereunder\b":          'Replace with "under that" or name the specific provision',
    r"\bwhereof\b":             'Replace with "of which"',
    r"\bwherein\b":             'Replace with "in which"',
    r"\bforthwith\b":           'Replace with "immediately"',
    r"\bnotwithstanding\b":     'Replace with "Despite" or "Even if"',
    r"\bin witness whereof\b":  'Replace with "Signed" or simply remove',
    r"\bpursuant to\b":         'Replace with "under" or "in accordance with"',
    r"\binter alia\b":          'Replace with "among other things"',
    r"\bmutatis mutandis\b":    'Replace with "with necessary changes"',
    r"\bpari passu\b":          'Replace with "equally" or "at the same rate"',
    r"\bforce majeure\b":       "Define explicitly in plain language what qualifies",
    r"\btime is of the essence\b": 'Replace with "all deadlines in this Agreement are strict and must be met"',
}


def flag_legalese(text: str) -> list[dict]:
    findings = []
    for pattern, replacement in LEGALESE_MAP.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            s, e, sentence = _extract_sentence(text, match.start(), match.end())
            # Build revised sentence by substituting the term
            revised_sentence = re.sub(pattern, replacement, sentence, flags=re.IGNORECASE).strip()
            # Clean up double spaces
            revised_sentence = re.sub(r" {2,}", " ", revised_sentence)
            findings.append({
                "type": "legalese",
                "term": match.group(),
                "start": match.start(),
                "end": match.end(),
                "suggestion": LEGALESE_HUMAN.get(pattern, f'Replace "{match.group()}" with plain language'),
                "original": sentence[:300],
                "revised": revised_sentence[:300] if revised_sentence != sentence.strip() else None,
                "context": sentence[:300],
            })
    return findings


# ── 2. Passive Voice ──────────────────────────────────────────────────────────

PASSIVE_PATTERN = re.compile(
    r"\b(is|are|was|were|be|been|being|shall be|will be|must be|should be|may be|can be)"
    r"\s+(\w+ed|awarded|done|given|made|paid|provided|required|sent|shown|taken|used|written)\b",
    re.IGNORECASE,
)

# Maps passive phrase → (active replacement, subject to prepend)
ACTIVE_REWRITES = {
    "is required":     ("shall", "The Contractor"),
    "are required":    ("shall", "The Contractor"),
    "shall be provided": ("shall provide", "The Contractor"),
    "shall be submitted": ("shall submit", "The Bidder"),
    "must be submitted": ("must submit", "The Bidder"),
    "must be provided": ("must provide", "The Contractor"),
    "will be evaluated": ("will evaluate", "Canada"),
    "will be reviewed":  ("will review", "Canada"),
    "will be assessed":  ("will assess", "Canada"),
    "is expected":     ("is expected to", "The Contractor"),
    "shall be paid":   ("shall pay", "Canada"),
    "will be paid":    ("will pay", "Canada"),
    "is required to":  ("shall", "The Contractor"),
}


def _rewrite_passive(sentence: str, match_phrase: str) -> str:
    """Attempt a best-effort active voice rewrite of a sentence."""
    phrase_lower = match_phrase.lower().strip()
    if phrase_lower in ACTIVE_REWRITES:
        active_verb, subject = ACTIVE_REWRITES[phrase_lower]
        # Replace passive construction with active
        rewritten = re.sub(
            re.escape(match_phrase),
            active_verb,
            sentence,
            count=1,
            flags=re.IGNORECASE,
        )
        # Prepend subject if sentence doesn't already start with it or "The"
        if not rewritten.strip().lower().startswith(subject.lower()):
            rewritten = f"{subject} {rewritten.strip().lstrip('it is that It Is That').strip()}"
        return re.sub(r" {2,}", " ", rewritten).strip()
    return f"[Rewrite in active voice — identify who performs the action and make them the subject]"


def flag_passive_voice(text: str) -> list[dict]:
    findings = []
    seen = set()

    for match in PASSIVE_PATTERN.finditer(text):
        s, e, sentence = _extract_sentence(text, match.start(), match.end())
        if s in seen:
            continue
        seen.add(s)
        revised = _rewrite_passive(sentence, match.group())
        findings.append({
            "type": "passive_voice",
            "term": match.group(),
            "start": match.start(),
            "end": match.end(),
            "suggestion": "Use active voice — identify who does the action and make them the subject.",
            "original": sentence[:300],
            "revised": revised[:300] if revised != sentence.strip() else None,
            "context": sentence[:300],
        })

    if nlp:
        doc = nlp(text[:50000])
        for token in doc:
            if token.dep_ == "nsubjpass":
                sent_text = token.sent.text.strip()
                s_char = token.sent.start_char
                if s_char in seen:
                    continue
                seen.add(s_char)
                findings.append({
                    "type": "passive_voice",
                    "term": sent_text[:80],
                    "start": s_char,
                    "end": token.sent.end_char,
                    "suggestion": "Use active voice — identify who does the action and make them the subject.",
                    "original": sent_text[:300],
                    "revised": "[Rewrite: identify who performs this action and make them the grammatical subject]",
                    "context": sent_text[:300],
                })

    return findings


# ── 3. Plural Party Terms ─────────────────────────────────────────────────────

PLURAL_PARTY_PATTERN = re.compile(
    r"\b(Bidders|Contractors|Proponents|Vendors|Suppliers|Respondents)"
    r"\s+(must|shall|should|will|are|may|have|need)\b",
)

SINGULAR_MAP = {
    "Bidders":     "The Bidder",
    "Contractors": "The Contractor",
    "Proponents":  "The Proponent",
    "Vendors":     "The Vendor",
    "Suppliers":   "The Supplier",
    "Respondents": "The Respondent",
}


def flag_plural_parties(text: str) -> list[dict]:
    findings = []
    for match in PLURAL_PARTY_PATTERN.finditer(text):
        plural = match.group(1)
        verb   = match.group(2)
        singular = SINGULAR_MAP.get(plural, f"The {plural.rstrip('s')}")
        s, e, sentence = _extract_sentence(text, match.start(), match.end())
        revised = sentence.replace(match.group(), f"{singular} {verb}", 1)
        findings.append({
            "type": "plural_parties",
            "term": match.group(),
            "start": match.start(),
            "end": match.end(),
            "suggestion": f'Replace "{plural}" with "{singular}" — singular is unambiguous in contract language.',
            "original": sentence[:300],
            "revised": revised[:300],
            "context": sentence[:300],
        })
    return findings


# ── 4. Gendered Language ──────────────────────────────────────────────────────

GENDERED_MAP = {
    r"\bhe\b":          "they",
    r"\bshe\b":         "they",
    r"\bhim\b":         "them",
    r"\bher\b":         "them",
    r"\bhis\b":         "their",
    r"\bhers\b":        "theirs",
    r"\bhimself\b":     "themselves",
    r"\bherself\b":     "themselves",
    r"\bhe or she\b":   "they",
    r"\bhis or her\b":  "their",
    r"\bhim or her\b":  "them",
    r"\bmanpower\b":    "workforce",
    r"\bmanmade\b":     "manufactured",
    r"\bworkman\b":     "worker",
    r"\bchairman\b":    "chair",
    r"\bsalesman\b":    "sales representative",
    r"\bforefathers\b": "predecessors",
}


def flag_gendered_language(text: str) -> list[dict]:
    findings = []
    for pattern, replacement in GENDERED_MAP.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            s, e, sentence = _extract_sentence(text, match.start(), match.end())
            revised = re.sub(pattern, replacement, sentence, flags=re.IGNORECASE)
            revised = re.sub(r" {2,}", " ", revised).strip()
            findings.append({
                "type": "gendered_language",
                "term": match.group(),
                "start": match.start(),
                "end": match.end(),
                "suggestion": f'Replace "{match.group()}" with "{replacement}" for gender-neutral language.',
                "original": sentence[:300],
                "revised": revised[:300] if revised != sentence.strip() else None,
                "context": sentence[:300],
            })
    return findings


# ── Master Lint Function ──────────────────────────────────────────────────────

def lint(text: str) -> dict:
    return {
        "legalese":         flag_legalese(text),
        "passive_voice":    flag_passive_voice(text),
        "plural_parties":   flag_plural_parties(text),
        "gendered_language": flag_gendered_language(text),
    }
