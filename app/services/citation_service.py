"""
citation_validator.py — McGill Guide Citation Validator
Validates Canadian legal citations against McGill Guide (10th ed.) formatting.

Covers:
  - Statutes (federal & provincial)
  - Regulations (SOR, SI, O Reg, etc.)
  - Cases (neutral citation + law report)
"""

import re
from dataclasses import dataclass


@dataclass
class CitationFinding:
    raw: str          # The matched citation text
    kind: str         # "statute" | "regulation" | "case"
    valid: bool       # True if format passes
    warnings: list    # List of warning strings
    start: int
    end: int


# ── Statute Patterns ─────────────────────────────────────────────────────────
#
# McGill format: Title (italicised), RS/SC/SBC/RSO/etc. year, chapter.
# Example: Business Corporations Act, RSC 1985, c B-3
#          Canadian Human Rights Act, RSC 1985, c H-6
#          Employment Standards Act, 2000, SO 2000, c 41
#
# Key rules:
#   - Title should be in italics (flagged as warning if not — can't detect in plain text)
#   - Abbreviation must match known federal/provincial codes
#   - Chapter format: "c" followed by letter-number or number

FEDERAL_STATUTE_CODES = r"RSC|SC|LRC"
PROVINCIAL_STATUTE_CODES = (
    r"RSA|SA|RSO|SO|SBC|RSBC|RSNB|SNB|RSNS|SNS"
    r"|RSPEI|SPEI|RSM|SM|RSS|SS|RSQ|SQ|RSNL|SNL"
    r"|RSNWT|SNWT|RSY|SY|RSNU|SNU"
)
ALL_STATUTE_CODES = f"(?:{FEDERAL_STATUTE_CODES}|{PROVINCIAL_STATUTE_CODES})"

# Statute regex:
#   Group 1: Title (one or more title-cased words, possibly with commas/years)
#   Group 2: Statute code
#   Group 3: Year
#   Group 4: Chapter designation
STATUTE_RE = re.compile(
    r"([A-Z][A-Za-z\s,']+?(?:Act|Code|Loi|Charter|Constitution)[\w\s,]*?)"  # Title
    r",\s*"
    r"(" + ALL_STATUTE_CODES + r")"                                           # Code
    r"\s+"
    r"(\d{4})"                                                                # Year
    r",\s*c\s+"                                                               # ", c "
    r"([A-Z]?\d+[-\.\d]*|[A-Z]-\d+)",                                        # Chapter
    re.UNICODE,
)

# Secondary pattern: common Canadian statute names referenced without a full RSC/SO citation.
# Catches standalone references like "the Competition Act" or "CFTA".
COMMON_STATUTE_NAMES = [
    "Competition Act",
    "Income Tax Act",
    "Privacy Act",
    "Personal Information Protection and Electronic Documents Act",
    "PIPEDA",
    "Canadian Human Rights Act",
    "Employment Insurance Act",
    "Canada Labour Code",
    "Financial Administration Act",
    "Lobbying Act",
    "Access to Information Act",
    "Official Languages Act",
    "Customs Act",
    "Excise Tax Act",
    "Bankruptcy and Insolvency Act",
    "Copyright Act",
    "Patent Act",
    "Trade-marks Act",
    "CFTA",
    "CUSMA",
    "CETA",
]

COMMON_STATUTE_RE = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in COMMON_STATUTE_NAMES) + r")\b",
    re.UNICODE,
)

# ── Regulation Patterns ───────────────────────────────────────────────────────
#
# Federal: SOR/YYYY-NNN  (Statutory Orders and Regulations)
#          SI/YYYY-NNN   (Statutory Instruments)
# Provincial: O Reg NNN/YY  (Ontario)
#             BC Reg NNN/YYYY
#
# McGill format: Title, SOR/2003-124
#                Title, SI/2018-76

REGULATION_RE = re.compile(
    r"([A-Z][A-Za-z\s,]+?(?:Regulation|Règlement|Order|Decree|Rules)[\w\s,]*?)"  # Title
    r",\s*"
    r"("
    r"SOR/\d{4}-\d+"           # Federal SOR
    r"|SI/\d{4}-\d+"           # Federal SI
    r"|O\s*Reg\s+\d+/\d{2,4}"  # Ontario
    r"|BC\s+Reg\s+\d+/\d{4}"   # BC
    r"|Alta\s+Reg\s+\d+/\d{4}" # Alberta
    r")",
    re.UNICODE,
)

# ── Case Patterns ─────────────────────────────────────────────────────────────
#
# Neutral citation (preferred): Style of Cause, YYYY Court NN
#   e.g. Heller v Uber Technologies Inc, 2020 SCC 16
#        R v Jordan, 2016 SCC 27
#        Canada (Minister of Justice) v Borowski, 1981 CanLII 34 (SCC)
#
# Law report citation: Style of Cause, [YYYY] Vol Reporter Page (Court)
#   e.g. R v Oakes, [1986] 1 SCR 103
#
# Rules:
#   - Style of cause italicised (warning only — can't detect in plain text)
#   - "v" not "v." or "vs" in Canadian citations
#   - Year in round brackets for neutral; square for law reports

NEUTRAL_COURTS = (
    r"SCC|FCA|FC|BCCA|BCSC|ONCA|ONSC|ONSC|QCCA|QCCS"
    r"|ABCA|ABQB|MBCA|MBQB|SKCA|SKQB|NSCA|NSSC"
    r"|NBCA|NBQB|NLCA|NLSC|PECA|PESC|YKCA|YKSC"
    r"|NWTCA|NWTSC|NUCA|NUSC|CanLII|ONCTJ|ONCJ"
)

NEUTRAL_CASE_RE = re.compile(
    r"([A-Z][A-Za-zÀ-ÿ\s'\(\)]+?(?:\sv\s|\svs\.\s|\sv\.\s)[A-Za-zÀ-ÿ\s',\(\)\.]+?)"  # Style of cause
    r",\s*"
    r"(\d{4})\s+"                    # Year
    r"(" + NEUTRAL_COURTS + r")"     # Court abbreviation
    r"\s+(\d+)"                      # Decision number
    r"(?:\s+\([A-Z]+\))?",           # Optional jurisdiction in parens
    re.UNICODE,
)

LAW_REPORT_CASE_RE = re.compile(
    r"([A-Z][A-Za-zÀ-ÿ\s'\(\)]+?(?:\sv\s|\svs\.\s|\sv\.\s)[A-Za-zÀ-ÿ\s',\(\)\.]+?)"
    r",\s*"
    r"\[(\d{4})\]\s+"                # [Year]
    r"(\d+\s+)?"                     # Optional volume
    r"([A-Z]{2,6})\s+"              # Reporter abbreviation
    r"(\d+)",                        # Page number
    re.UNICODE,
)


# ── Validation Logic ──────────────────────────────────────────────────────────

def validate_statute(match: re.Match, text: str) -> CitationFinding:
    warnings = []
    raw = match.group(0)
    title = match.group(1).strip()
    code = match.group(2)
    year = int(match.group(3))
    chapter = match.group(4)

    # Warning: title should be italicised in formatted documents
    warnings.append("⚠️ Ensure the Act title is italicised in the final document.")

    # Check year is plausible
    if year < 1867 or year > 2030:
        warnings.append(f"⚠️ Year {year} seems implausible for a Canadian statute.")

    # Federal RSC should be 1985 or earlier consolidated version
    if code == "RSC" and year not in (1985, 1970, 1952, 1927, 1906):
        warnings.append(
            f"⚠️ 'RSC {year}' is unusual — RSC consolidations are typically RSC 1985, RSC 1970, etc. "
            f"Use 'SC {year}' for session laws."
        )

    # Chapter format check: should be letter-number (B-3) or plain number
    if not re.match(r"^[A-Z]-\d+$|^\d+$|^[A-Z]\d+$", chapter):
        warnings.append(f"⚠️ Chapter '{chapter}' format looks non-standard. Expected e.g. 'c B-3' or 'c 41'.")

    return CitationFinding(
        raw=raw, kind="statute", valid=len(warnings) <= 1,
        warnings=warnings, start=match.start(), end=match.end()
    )


def validate_regulation(match: re.Match, text: str) -> CitationFinding:
    warnings = []
    raw = match.group(0)

    # Warning: title should be italicised
    warnings.append("⚠️ Ensure the Regulation title is italicised in the final document.")

    # SOR number format check
    ref = match.group(2)
    if ref.startswith("SOR/"):
        # SOR/YYYY-NNN
        sor_match = re.match(r"SOR/(\d{4})-(\d+)", ref)
        if sor_match:
            year = int(sor_match.group(1))
            if year < 1955 or year > 2030:
                warnings.append(f"⚠️ SOR year {year} looks implausible.")
        else:
            warnings.append("⚠️ SOR number format should be SOR/YYYY-NNN (e.g., SOR/2003-124).")

    return CitationFinding(
        raw=raw, kind="regulation", valid=True,
        warnings=warnings, start=match.start(), end=match.end()
    )


def validate_case(match: re.Match, kind: str, text: str) -> CitationFinding:
    warnings = []
    raw = match.group(0)
    style = match.group(1).strip()

    # McGill uses "v" without a period — flag "vs" or "v."
    if re.search(r"\bvs\.?\b", style, re.IGNORECASE):
        warnings.append('⚠️ Canadian citations use "v" not "vs" or "vs." in the style of cause.')
    if re.search(r"\bv\.\b", style):
        warnings.append('⚠️ Canadian citations use "v" not "v." (no period) in the style of cause.')

    # Style of cause should be italicised
    warnings.append("⚠️ Ensure the style of cause is italicised in the final document.")

    # For neutral citations, year in round brackets is NOT used (year is plain)
    if kind == "neutral":
        year = match.group(2)
        court = match.group(3)
        number = match.group(4)
        if not court:
            warnings.append("⚠️ Neutral citation missing court abbreviation (e.g., SCC, ONCA).")

    return CitationFinding(
        raw=raw, kind="case", valid=True,
        warnings=warnings, start=match.start(), end=match.end()
    )


# ── Main Validator ────────────────────────────────────────────────────────────

def validate_citations(text: str) -> list[CitationFinding]:
    """
    Scan text for all Canadian legal citations and validate against McGill Guide.
    Returns a list of CitationFinding objects.
    """
    findings = []
    seen_spans = set()

    def add(finding):
        span = (finding.start, finding.end)
        if span not in seen_spans:
            seen_spans.add(span)
            findings.append(finding)

    for match in STATUTE_RE.finditer(text):
        add(validate_statute(match, text))

    for match in COMMON_STATUTE_RE.finditer(text):
        span = (match.start(), match.end())
        if span not in seen_spans:
            seen_spans.add(span)
            findings.append(CitationFinding(
                raw=match.group(0),
                kind="statute",
                valid=True,
                warnings=["⚠️ Ensure the Act title is italicised in the final document."],
                start=match.start(),
                end=match.end(),
            ))

    for match in REGULATION_RE.finditer(text):
        add(validate_regulation(match, text))

    for match in NEUTRAL_CASE_RE.finditer(text):
        add(validate_case(match, "neutral", text))

    for match in LAW_REPORT_CASE_RE.finditer(text):
        add(validate_case(match, "law_report", text))

    return sorted(findings, key=lambda f: f.start)


def citation_summary(text: str) -> dict:
    findings = validate_citations(text)
    return {
        "total": len(findings),
        "statutes": [f for f in findings if f.kind == "statute"],
        "regulations": [f for f in findings if f.kind == "regulation"],
        "cases": [f for f in findings if f.kind == "case"],
        "all": findings,
    }
