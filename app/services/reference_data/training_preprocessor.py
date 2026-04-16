"""
Advanced training data — Part 5: Document preprocessing toolkit.
Markdown converter, legalese fixer, quality filter, and structured templates.
"""
import re
import json


# ── Legalese Finder & Fixer ──────────────────────────────────

LEGALESE_FILTERS = [
    (r"\bnotwithstanding the fact that\b", "although"),
    (r"\bat this point in time\b", "now"),
    (r"\bin the event that\b", "if"),
    (r"\bprior to\b", "before"),
    (r"\bsubsequent to\b", "after"),
    (r"\butilize\b", "use"),
    (r"\bfor the purpose of\b", "to"),
    (r"\bin accordance with\b", "under"),
    (r"\bwith respect to\b", "about"),
    (r"\bin connection with\b", "about"),
    (r"\bby virtue of\b", "because of"),
    (r"\bin order to\b", "to"),
    (r"\bgive consideration to\b", "consider"),
    (r"\bmake provision for\b", "provide for"),
    (r"\bhave knowledge of\b", "know"),
    (r"\bis in possession of\b", "has"),
    (r"\bmake a determination\b", "determine"),
    (r"\beffectuate\b", "carry out"),
    (r"\bhereinbefore\b", "above"),
    (r"\bhereinafter\b", "below"),
    (r"\bherein\b", "in this Agreement"),
    (r"\bhereto\b", "to this Agreement"),
    (r"\bhereof\b", "of this Agreement"),
    (r"\bthereby\b", "by that"),
    (r"\baforesaid\b", "[use specific reference]"),
    (r"\bwhereas\b", "[remove — use Background section]"),
    (r"\bwherefore\b", "[remove — state directly]"),
    (r"\bin witness whereof\b", "Signed"),
    (r"\bforce majeure\b", "unforeseeable event beyond a party's control"),
    (r"\binter alia\b", "among other things"),
    (r"\bmutatis mutandis\b", "with necessary changes"),
    (r"\bpari passu\b", "equally and without preference"),
]


def clean_legalese(text: str) -> dict:
    """Apply legalese filters and return cleaned text with change log."""
    changes = []
    cleaned = text
    for pattern, replacement in LEGALESE_FILTERS:
        matches = re.findall(pattern, cleaned, re.IGNORECASE)
        if matches:
            for match in matches:
                changes.append({"found": match, "replacement": replacement})
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    return {"original": text, "cleaned": cleaned, "changes": changes, "total_fixes": len(changes)}


# ── Markdown Document Converter ──────────────────────────────

def contract_to_markdown(text: str, metadata: dict = None) -> str:
    """
    Convert raw contract text to structured Markdown with YAML header.
    Designed as a preprocessing step for SLM training data.
    """
    lines = []

    # YAML header
    if metadata:
        lines.append("---")
        for k, v in metadata.items():
            lines.append(f'{k}: "{v}"')
        lines.append("---")
        lines.append("")

    # Process text sections
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue

        # Detect article/section headers
        if re.match(r"^(ARTICLE|Article)\s+\d+", stripped):
            lines.append(f"## {stripped}")
        elif re.match(r"^\d+\.\d+\s+[A-Z]", stripped):
            lines.append(f"### {stripped}")
        elif re.match(r"^\d+\.\d+\.\d+\s", stripped):
            lines.append(f"#### {stripped}")
        elif re.match(r"^(SCHEDULE|Schedule|APPENDIX|Appendix)\s+[A-Z]", stripped):
            lines.append(f"## {stripped}")
        elif stripped.isupper() and len(stripped) < 80:
            lines.append(f"## {stripped}")
        else:
            # Highlight deontic modals
            processed = stripped
            processed = re.sub(r"\bshall\b", "MUST", processed)
            processed = re.sub(r"\bShall\b", "MUST", processed)
            processed = re.sub(r"\bmay\b", "MAY", processed, flags=re.IGNORECASE)
            lines.append(processed)

    return "\n".join(lines)


# ── Quality Scoring ──────────────────────────────────────────

def score_training_sample(text: str) -> dict:
    """
    Score a training sample for SLM quality on 4 criteria (1-5 each).
    Returns score, verdict, and top issue.
    """
    clarity = 5
    structure = 5
    density = 5
    formatting = 5
    issues = []

    # Clarity: penalize legalese
    legalese_count = 0
    for pattern, _ in LEGALESE_FILTERS:
        legalese_count += len(re.findall(pattern, text, re.IGNORECASE))
    if legalese_count > 5:
        clarity = 1
        issues.append(f"{legalese_count} legalese terms found — needs full rewrite")
    elif legalese_count > 2:
        clarity = 3
        issues.append(f"{legalese_count} legalese terms found")
    elif legalese_count > 0:
        clarity = 4
        issues.append(f"{legalese_count} minor legalese term(s)")

    # Structure: check for hierarchy markers
    has_headers = bool(re.search(r"^#{1,4}\s", text, re.MULTILINE))
    has_lists = bool(re.search(r"^[-*]\s", text, re.MULTILINE))
    if not has_headers and not has_lists and len(text) > 500:
        structure = 2
        issues.append("No structural markers (headers/lists) in long text")
    elif not has_headers:
        structure = 3
        issues.append("No section headers found")

    # Density: penalize very short or very repetitive
    words = text.split()
    if len(words) < 20:
        density = 2
        issues.append("Too short — low informational density")
    unique_ratio = len(set(words)) / max(len(words), 1)
    if unique_ratio < 0.3:
        density = 2
        issues.append("High repetition — low unique word ratio")

    # Formatting: check defined terms, caps modals
    has_bold = "**" in text
    has_caps_modals = bool(re.search(r"\b(MUST|MAY|SHALL)\b", text))
    if not has_bold and not has_caps_modals:
        formatting = 3
        issues.append("No bold defined terms or capitalized modals")

    total = clarity + structure + density + formatting
    verdict = "PASS" if total >= 16 else "REVISE" if total >= 10 else "FAIL"

    return {
        "scores": {
            "clarity": clarity,
            "structure": structure,
            "density": density,
            "formatting": formatting,
        },
        "total": f"{total}/20",
        "verdict": verdict,
        "top_issue": issues[0] if issues else "No issues found",
        "all_issues": issues,
    }


# ── Training Data: Legalese Rewrite Pairs ────────────────────

LEGALESE_REWRITE_TRAINING = [
    {
        "instruction": "Rewrite this contract clause to remove legalese. Apply plain language principles: replace archaic terms, use active voice, use 'must' for obligations.",
        "input": "Notwithstanding the fact that the parties hereto have, prior to the execution hereof, utilized best endeavours in order to effectuate an agreement with respect to the aforesaid matters, in the event that a dispute arises subsequent to the date hereof, the parties shall give consideration to resolving same in accordance with the dispute resolution provisions hereinbefore set forth.",
        "output": "Although the parties used best efforts to reach agreement on these matters before signing, if a dispute arises after the date of this Agreement, the parties must consider resolving it under the dispute resolution provisions in Section [X] above."
    },
    {
        "instruction": "Rewrite this contract clause to remove legalese. Apply plain language principles.",
        "input": "In witness whereof the parties hereto have caused this Agreement to be executed by their duly authorized representatives as of the day and year first above written, it being understood that this instrument shall be binding upon the parties, their successors, and assigns.",
        "output": "The parties have signed this Agreement on the date set out above. This Agreement binds each party, its successors, and its assigns."
    },
    {
        "instruction": "Rewrite this contract clause to remove legalese. Apply plain language principles.",
        "input": "For the purpose of making a determination as to whether the Contractor is in possession of the requisite qualifications, the Contracting Authority shall, subsequent to bid closing, have knowledge of and access to all documentation submitted by virtue of the Contractor's response to this solicitation.",
        "output": "To determine whether the Contractor is qualified, the Contracting Authority must review all documentation the Contractor submitted in its bid response."
    },
    {
        "instruction": "Rewrite this contract clause to remove legalese. Apply plain language principles.",
        "input": "The Vendor hereby represents and warrants that, inter alia, it has not, at this point in time or at any time prior to the date hereof, directly or indirectly, effectuated any payment or given consideration to any public official for the purpose of obtaining or retaining business in connection with this Agreement.",
        "output": "The Vendor represents and warrants that it has not, directly or indirectly, paid or given anything of value to any public official to obtain or keep business related to this Agreement."
    },
]

# ── Training Data: Markdown Conversion Pairs ─────────────────

MARKDOWN_CONVERSION_TRAINING = [
    {
        "instruction": "Convert this raw contract text to structured Markdown suitable for SLM training. Add YAML metadata header, proper heading hierarchy, and highlight defined terms and deontic modals.",
        "input": "MASTER SERVICE AGREEMENT. This Master Service Agreement (the Agreement) is entered into as of January 1, 2025 (the Effective Date) between ABC Corp (the Client) and XYZ Services Inc (the Provider). ARTICLE 1 DEFINITIONS. 1.1 Confidential Information means any information disclosed by either party that is marked as confidential. 1.2 Deliverables means the work product to be delivered under a Statement of Work. 1.3 Service Levels means the performance standards in Schedule B. ARTICLE 2 SERVICES. 2.1 Scope The Provider shall provide the Services described in each Statement of Work. 2.2 Standard of Care The Provider shall perform the Services in a professional manner consistent with industry standards.",
        "output": "---\ndocument_type: \"Contract\"\njurisdiction: \"Canada/Ontario\"\ncomplexity_score: 3\n---\n\n# Master Service Agreement\n\nThis Master Service Agreement (the **Agreement**) is entered into as of January 1, 2025 (the **Effective Date**) between **ABC Corp** (the **Client**) and **XYZ Services Inc** (the **Provider**).\n\n## Article 1: Definitions\n\n### 1.1 Confidential Information\n**Confidential Information** means any information disclosed by either party that is marked as confidential.\n\n### 1.2 Deliverables\n**Deliverables** means the work product to be delivered under a Statement of Work.\n\n### 1.3 Service Levels\n**Service Levels** means the performance standards in Schedule B.\n\n## Article 2: Services\n\n### 2.1 Scope\nThe Provider MUST provide the Services described in each Statement of Work.\n\n### 2.2 Standard of Care\nThe Provider MUST perform the Services in a professional manner consistent with industry standards."
    },
    {
        "instruction": "Convert this RFP excerpt to structured Markdown for SLM training.",
        "input": "REQUEST FOR PROPOSAL. Solicitation No EN578-230045. Title Enterprise Data Analytics Platform. Closing Date June 15 2025 1400 ET. SECTION 1 OVERVIEW. The Government of Canada requires a cloud-based data analytics platform. SECTION 2 MANDATORY REQUIREMENTS. M1 The Bidder must demonstrate ISO 27001 certification. M2 The Bidder must have completed 3 similar projects in the last 5 years. M3 All data must reside in Canada. SECTION 3 RATED CRITERIA. R1 Technical Approach 40 points. R2 Experience and Qualifications 20 points. R3 Management Approach 10 points. Minimum technical score 50 out of 70.",
        "output": "---\ndocument_type: \"Procurement/RFP\"\njurisdiction: \"Canada/Federal\"\ncomplexity_score: 3\n---\n\n# Request for Proposal\n\n- **Solicitation No:** EN578-230045\n- **Title:** Enterprise Data Analytics Platform\n- **Closing Date:** June 15, 2025, 14:00 ET\n\n## Section 1: Overview\n\nThe Government of Canada requires a cloud-based data analytics platform.\n\n## Section 2: Mandatory Requirements\n\n- **M1:** The Bidder MUST demonstrate ISO 27001 certification.\n- **M2:** The Bidder MUST have completed 3 similar projects in the last 5 years.\n- **M3:** All data MUST reside in Canada.\n\n## Section 3: Rated Criteria\n\n| Criterion | Points |\n|-----------|--------|\n| R1: Technical Approach | 40 |\n| R2: Experience and Qualifications | 20 |\n| R3: Management Approach | 10 |\n| **Total** | **70** |\n\n- **Minimum technical score:** 50 out of 70"
    },
]

# ── Training Data: Quality Audit Pairs ───────────────────────

QUALITY_AUDIT_TRAINING = [
    {
        "instruction": "Grade this training sample for SLM ingestion. Score on Clarity (1-5), Structural Integrity (1-5), Density (1-5), and Formatting (1-5). Return JSON with scores, verdict (PASS/FAIL/REVISE), and top issue.",
        "input": "The Contractor hereto shall, notwithstanding the aforesaid provisions hereinbefore set forth, utilize best endeavours in order to effectuate the delivery of the goods prior to the date specified in Schedule A, it being understood that in the event that the Contractor fails to deliver same, Canada shall, subsequent to providing notice, have the right to terminate this Agreement for default.",
        "output": '{"scores": {"clarity": 1, "structure": 2, "density": 3, "formatting": 1}, "total": "7/20", "verdict": "FAIL", "top_issue": "Severe legalese contamination — 8+ archaic terms (hereto, notwithstanding, aforesaid, hereinbefore, utilize, effectuate, prior to, subsequent to, same). Must be fully rewritten in plain language.", "rewritten": "The Contractor must use best efforts to deliver the goods by the date in Schedule A. If the Contractor fails to deliver, Canada may terminate this Agreement for default after giving notice."}'
    },
    {
        "instruction": "Grade this training sample for SLM ingestion. Score on Clarity (1-5), Structural Integrity (1-5), Density (1-5), and Formatting (1-5).",
        "input": "## 5.1 Data Breach Notification\n\nThe **Processor** MUST notify the **Controller** within 24 hours of discovering a data breach. The notification MUST include:\n\n- Nature and scope of the breach\n- Categories of **Personal Data** affected\n- Approximate number of **Data Subjects** affected\n- Measures taken to contain the breach\n- Proposed remediation plan\n\nFailure to notify within 24 hours constitutes a material breach of this Agreement.",
        "output": '{"scores": {"clarity": 5, "structure": 5, "density": 5, "formatting": 5}, "total": "20/20", "verdict": "PASS", "top_issue": "No issues found. Excellent training sample — clear hierarchy, bold defined terms, caps modals, specific deadline, and stated consequence."}'
    },
]


# ── Combined export ──────────────────────────────────────────

ALL_PREPROCESSOR_TRAINING = (
    LEGALESE_REWRITE_TRAINING
    + MARKDOWN_CONVERSION_TRAINING
    + QUALITY_AUDIT_TRAINING
)
