"""
dark_obligation_service.py — Lexara "Blast Radius" Step 4

Detects clauses that are MISSING from a SOW but appear in a high percentage of
peer contracts of the same type.

A truly novel SOW review doesn't just read what's on the page — it knows what
is *not* there. Example:
    "This is an IT service contract, but no Data Breach Notification SLA is
     specified. 94% of peer IT contracts include a 24-hour notification clause.
     Recommend inserting Standard Clause #4."

For Phase 1 the contract type is supplied by the caller; the catalog of
"standard" clauses per contract type is hand-curated below as a Python constant
(no DB migration). Peer frequencies are taken from observed industry norms
across Canadian public-sector procurement and standard commercial templates;
they may later be replaced with live percentages once we have enough indexed
contracts to compute them empirically.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.nlp.embeddings import cosine_similarity, embed_text

logger = logging.getLogger(__name__)


# ── Standard clause catalog, scoped by contract type ─────────────────────────
#
# Each entry:
#   key              — stable identifier (snake_case)
#   label            — human-readable name
#   peer_frequency   — fraction of peer contracts of this type that include it
#   importance       — "critical" | "high" | "medium" | "low"
#   typical_text     — 1-2 sentence template used as the embedding probe
#   rationale        — why its absence matters
#
# Frequencies are estimates anchored to publicly-available standard-form
# contracts (PSPC SACC, NEC4, AIA, IACCM benchmarks). They are deliberately
# conservative for Phase 1.

STANDARD_CLAUSE_CATALOG: dict[str, list[dict]] = {
    "it_services": [
        {
            "key": "data_breach_notification",
            "label": "Data Breach Notification SLA",
            "peer_frequency": 0.94,
            "importance": "critical",
            "typical_text": (
                "Vendor shall notify the Buyer in writing within 24 hours of "
                "discovery of any data breach, security incident, or unauthorized "
                "access to personal information."
            ),
            "rationale": (
                "Required under PIPEDA / GDPR-equivalents; absence creates "
                "regulatory exposure and prevents timely buyer response."
            ),
        },
        {
            "key": "data_residency",
            "label": "Data Residency Clause",
            "peer_frequency": 0.88,
            "importance": "high",
            "typical_text": (
                "All Buyer data shall be stored and processed exclusively within "
                "Canadian data centres and shall not be transferred outside Canada "
                "without prior written consent."
            ),
            "rationale": (
                "Canadian public-sector buyers face statutory residency requirements; "
                "missing this clause exposes the buyer to cross-border-transfer risk."
            ),
        },
        {
            "key": "uptime_sla",
            "label": "Uptime / Availability SLA",
            "peer_frequency": 0.91,
            "importance": "high",
            "typical_text": (
                "The Service shall be available not less than 99.9% of the time "
                "measured monthly, with service credits payable for any shortfall."
            ),
            "rationale": (
                "Without a measurable availability commitment the buyer has no "
                "remedy for chronic outages."
            ),
        },
        {
            "key": "right_to_audit",
            "label": "Right-to-Audit Clause",
            "peer_frequency": 0.79,
            "importance": "high",
            "typical_text": (
                "Buyer or its appointed auditor shall have the right, on reasonable "
                "notice, to audit Vendor's records, controls, and security posture "
                "relevant to the Services."
            ),
            "rationale": (
                "Audit rights are required for SOC 2, ISO 27001 alignment and "
                "for Treasury Board oversight of suppliers."
            ),
        },
        {
            "key": "subprocessor_disclosure",
            "label": "Subprocessor Disclosure",
            "peer_frequency": 0.72,
            "importance": "medium",
            "typical_text": (
                "Vendor shall maintain and disclose on request a current list of "
                "all subprocessors handling Buyer data, and shall obtain prior "
                "written consent before adding new subprocessors."
            ),
            "rationale": (
                "Hidden subprocessing chains are a leading cause of supply-chain "
                "data incidents; disclosure is now a baseline expectation."
            ),
        },
        {
            "key": "exit_data_return",
            "label": "Exit / Data Return Obligation",
            "peer_frequency": 0.83,
            "importance": "high",
            "typical_text": (
                "Upon termination or expiry, Vendor shall return all Buyer data "
                "in a structured machine-readable format and shall securely delete "
                "all copies within thirty (30) days, providing written certification."
            ),
            "rationale": (
                "Without an exit clause, buyers can be locked into vendors via "
                "their own data; it is the single most-cited gap in IT post-mortems."
            ),
        },
        {
            "key": "security_certification",
            "label": "Security Certification Requirement",
            "peer_frequency": 0.68,
            "importance": "medium",
            "typical_text": (
                "Vendor shall maintain a current SOC 2 Type II or ISO/IEC 27001 "
                "certification covering the Services and shall provide the latest "
                "report on request."
            ),
            "rationale": (
                "Independent attestation is the standard floor for IT-services "
                "buyers; absence is a procurement-policy red flag."
            ),
        },
        {
            "key": "privacy_impact_assessment",
            "label": "Privacy Impact Assessment Cooperation",
            "peer_frequency": 0.61,
            "importance": "medium",
            "typical_text": (
                "Vendor shall cooperate with the Buyer in completing any Privacy "
                "Impact Assessment required by applicable law or by the Buyer's "
                "internal policies."
            ),
            "rationale": (
                "Federal departments must complete a PIA; the contract should "
                "obligate the vendor's cooperation."
            ),
        },
    ],
    "goods": [
        {
            "key": "warranty_period",
            "label": "Warranty Period",
            "peer_frequency": 0.96,
            "importance": "critical",
            "typical_text": (
                "Supplier warrants the Goods against defects in materials and "
                "workmanship for a period of twelve (12) months from the date of "
                "acceptance."
            ),
            "rationale": (
                "Without an explicit warranty period the buyer is left with only "
                "implied statutory warranties, which are narrower."
            ),
        },
        {
            "key": "inspection_acceptance",
            "label": "Inspection and Acceptance",
            "peer_frequency": 0.93,
            "importance": "high",
            "typical_text": (
                "Buyer shall have thirty (30) days from delivery to inspect the "
                "Goods and may reject any Goods that do not conform to the "
                "specifications."
            ),
            "rationale": (
                "Defines the buyer's window to refuse non-conforming goods; "
                "absence shifts the risk onto the buyer."
            ),
        },
        {
            "key": "title_transfer",
            "label": "Title and Risk of Loss",
            "peer_frequency": 0.89,
            "importance": "high",
            "typical_text": (
                "Title to and risk of loss for the Goods shall pass to Buyer upon "
                "delivery to the destination specified in the purchase order."
            ),
            "rationale": (
                "Ambiguity over when title transfers is a frequent source of "
                "loss-allocation disputes during shipping incidents."
            ),
        },
        {
            "key": "force_majeure",
            "label": "Force Majeure",
            "peer_frequency": 0.85,
            "importance": "medium",
            "typical_text": (
                "Neither party shall be liable for delay or failure to perform "
                "caused by events beyond its reasonable control, including acts of "
                "God, war, pandemic, or government action."
            ),
            "rationale": (
                "Supply-chain shocks since 2020 have made force-majeure language "
                "table-stakes for goods contracts."
            ),
        },
        {
            "key": "country_of_origin",
            "label": "Country of Origin Disclosure",
            "peer_frequency": 0.71,
            "importance": "medium",
            "typical_text": (
                "Supplier shall disclose the country of origin for all Goods and "
                "shall comply with all applicable Canadian content and trade "
                "agreement requirements."
            ),
            "rationale": (
                "Required for CETA/CFTA/USMCA compliance and for Government of "
                "Canada Buy Canadian preferences."
            ),
        },
        {
            "key": "packaging_shipping",
            "label": "Packaging and Shipping Standards",
            "peer_frequency": 0.66,
            "importance": "low",
            "typical_text": (
                "Goods shall be packaged in accordance with industry standards "
                "sufficient to prevent damage in transit and shall be shipped in "
                "accordance with the agreed Incoterms."
            ),
            "rationale": (
                "Without a packaging standard, in-transit damage disputes default "
                "to general carriage law, which favors the carrier."
            ),
        },
    ],
    "construction": [
        {
            "key": "performance_bond",
            "label": "Performance Bond Requirement",
            "peer_frequency": 0.92,
            "importance": "critical",
            "typical_text": (
                "Contractor shall provide a performance bond equal to fifty "
                "percent (50%) of the contract price, issued by a surety acceptable "
                "to the Owner."
            ),
            "rationale": (
                "Standard public-works requirement; without it the owner has no "
                "protection against contractor default mid-build."
            ),
        },
        {
            "key": "lien_holdback",
            "label": "Statutory Lien Holdback",
            "peer_frequency": 0.95,
            "importance": "critical",
            "typical_text": (
                "Owner shall withhold the statutory holdback of ten percent (10%) "
                "from each progress payment in accordance with the applicable "
                "Construction Lien Act."
            ),
            "rationale": (
                "Mandatory under provincial construction-lien statutes; failure "
                "to hold back exposes the owner to subcontractor lien claims."
            ),
        },
        {
            "key": "site_safety",
            "label": "Site Safety and OHS Compliance",
            "peer_frequency": 0.97,
            "importance": "critical",
            "typical_text": (
                "Contractor shall comply with all Occupational Health and Safety "
                "legislation applicable at the site and shall act as the Constructor "
                "for OHS purposes unless otherwise agreed."
            ),
            "rationale": (
                "OHS prosecutions can pierce to the owner if Constructor status is "
                "ambiguous; this clause is non-negotiable in modern Canadian builds."
            ),
        },
        {
            "key": "change_order_process",
            "label": "Change Order Process",
            "peer_frequency": 0.90,
            "importance": "high",
            "typical_text": (
                "Any change to the Work shall be authorized only by a written "
                "change order signed by both parties before the change is performed, "
                "and shall include any adjustment to price and schedule."
            ),
            "rationale": (
                "Verbal change requests are the leading cause of construction "
                "claims; a formal process is essential."
            ),
        },
        {
            "key": "delay_damages",
            "label": "Liquidated Damages for Delay",
            "peer_frequency": 0.74,
            "importance": "high",
            "typical_text": (
                "Should the Contractor fail to achieve Substantial Performance by "
                "the Completion Date, Contractor shall pay liquidated damages of "
                "$X per day until Substantial Performance is achieved."
            ),
            "rationale": (
                "Without liquidated damages the owner must prove actual loss for "
                "delay — a costly and uncertain process."
            ),
        },
        {
            "key": "warranty_correction",
            "label": "Warranty / Correction of Defects Period",
            "peer_frequency": 0.88,
            "importance": "high",
            "typical_text": (
                "Contractor shall correct, at its own cost, any defects in the "
                "Work that appear within twelve (12) months of Substantial "
                "Performance."
            ),
            "rationale": (
                "Standard CCDC/CCA term; without it, defect remediation depends "
                "on negligence proof."
            ),
        },
    ],
    "consulting": [
        {
            "key": "ip_ownership",
            "label": "IP Ownership of Deliverables",
            "peer_frequency": 0.93,
            "importance": "critical",
            "typical_text": (
                "All deliverables produced under this engagement shall be the "
                "exclusive property of the Client upon payment, and Consultant "
                "hereby assigns all such intellectual property rights to Client."
            ),
            "rationale": (
                "Without explicit assignment, IP in commissioned work may default "
                "to the consultant under copyright law."
            ),
        },
        {
            "key": "non_solicitation",
            "label": "Non-Solicitation of Personnel",
            "peer_frequency": 0.78,
            "importance": "medium",
            "typical_text": (
                "During the engagement and for twelve (12) months thereafter, "
                "neither party shall solicit for employment any personnel of the "
                "other party who was directly involved in the engagement."
            ),
            "rationale": (
                "Protects both sides from staff poaching; common boilerplate "
                "in professional-services agreements."
            ),
        },
        {
            "key": "deliverable_acceptance",
            "label": "Deliverable Acceptance Criteria",
            "peer_frequency": 0.86,
            "importance": "high",
            "typical_text": (
                "Each deliverable shall be deemed accepted unless Client provides "
                "written notice of rejection with specific deficiencies within "
                "fifteen (15) business days of delivery."
            ),
            "rationale": (
                "Without acceptance criteria, payment disputes drag indefinitely."
            ),
        },
        {
            "key": "conflict_of_interest",
            "label": "Conflict of Interest Disclosure",
            "peer_frequency": 0.69,
            "importance": "medium",
            "typical_text": (
                "Consultant shall promptly disclose to Client any actual or "
                "potential conflict of interest arising from work performed for "
                "other clients."
            ),
            "rationale": (
                "Required for federal advisory engagements under the Values and "
                "Ethics Code; standard in public-sector consulting contracts."
            ),
        },
        {
            "key": "professional_liability",
            "label": "Professional Liability Insurance",
            "peer_frequency": 0.81,
            "importance": "high",
            "typical_text": (
                "Consultant shall maintain professional liability (errors and "
                "omissions) insurance of not less than $2,000,000 per claim and "
                "shall provide a certificate on request."
            ),
            "rationale": (
                "E&O is the primary remedy when professional advice causes loss; "
                "without minimums the buyer has no assurance of recovery."
            ),
        },
        {
            "key": "key_personnel",
            "label": "Key Personnel Substitution Restrictions",
            "peer_frequency": 0.64,
            "importance": "medium",
            "typical_text": (
                "Consultant shall not substitute the Key Personnel named in the "
                "Statement of Work without the prior written consent of Client, "
                "such consent not to be unreasonably withheld."
            ),
            "rationale": (
                "Buyers select consultancies based on named individuals; "
                "uncontrolled substitution is a frequent quality-of-service issue."
            ),
        },
    ],
}


# ── Internal helpers ─────────────────────────────────────────────────────────


def _chunk_sow(sow_text: str, max_chunks: int = 50) -> list[str]:
    """
    Split the SOW into reasonable chunks for per-clause similarity scoring.
    Splits on double-newlines (paragraph breaks); falls back to whole text
    if there are no paragraph breaks.
    """
    chunks = [c.strip() for c in sow_text.split("\n\n") if c.strip()]
    if not chunks:
        chunks = [sow_text.strip()]
    # Cap to keep embedding cost bounded for very long SOWs
    if len(chunks) > max_chunks:
        # Merge to roughly max_chunks groups
        group_size = (len(chunks) + max_chunks - 1) // max_chunks
        merged: list[str] = []
        for i in range(0, len(chunks), group_size):
            merged.append("\n\n".join(chunks[i : i + group_size]))
        chunks = merged
    return chunks


def _max_similarity(probe_text: str, chunks: list[str]) -> float:
    """Return the maximum cosine similarity between the probe and any chunk."""
    if not chunks:
        return 0.0
    probe_vec = embed_text(probe_text)
    best = 0.0
    for chunk in chunks:
        try:
            chunk_vec = embed_text(chunk)
            score = cosine_similarity(probe_vec, chunk_vec)
            if score > best:
                best = score
        except Exception as e:  # pragma: no cover — defensive
            logger.warning(f"Embedding failed for chunk (len={len(chunk)}): {e}")
            continue
    return float(best)


# ── Public API ───────────────────────────────────────────────────────────────


def list_supported_contract_types() -> list[str]:
    """Return the list of contract-type keys this service can analyse."""
    return sorted(STANDARD_CLAUSE_CATALOG.keys())


def get_catalog_for(contract_type: str) -> Optional[list[dict]]:
    """Return the curated clause catalog for one contract type, or None."""
    return STANDARD_CLAUSE_CATALOG.get(contract_type)


def detect_dark_obligations(
    sow_text: str,
    contract_type: str,
    presence_threshold: float = 0.55,
    min_peer_frequency: float = 0.50,
) -> dict:
    """
    Detect "dark obligations" — clauses that peers commonly include but that
    are missing from this SOW.

    Args:
        sow_text:           the full statement-of-work / contract text.
        contract_type:      one of the keys in STANDARD_CLAUSE_CATALOG.
        presence_threshold: cosine similarity above which a probe is treated
                            as "present" in the SOW (default 0.55).
        min_peer_frequency: only flag missing clauses whose peer-frequency is
                            at least this value (default 0.50).

    Returns: dict with keys
        contract_type, checked, missing, present, summary
        (or {error, message, supported_contract_types} on bad input).
    """
    catalog = STANDARD_CLAUSE_CATALOG.get(contract_type)
    if catalog is None:
        return {
            "error": "unsupported_contract_type",
            "message": (
                f"Contract type '{contract_type}' is not supported. "
                f"Supported types: {', '.join(list_supported_contract_types())}."
            ),
            "supported_contract_types": list_supported_contract_types(),
        }

    chunks = _chunk_sow(sow_text)
    missing: list[dict] = []
    present: list[dict] = []

    for entry in catalog:
        score = _max_similarity(entry["typical_text"], chunks)
        is_present = score >= presence_threshold

        if is_present:
            present.append(
                {
                    "key": entry["key"],
                    "label": entry["label"],
                    "best_match_score": round(score, 4),
                }
            )
        else:
            if entry["peer_frequency"] >= min_peer_frequency:
                missing.append(
                    {
                        "key": entry["key"],
                        "label": entry["label"],
                        "peer_frequency": entry["peer_frequency"],
                        "importance": entry["importance"],
                        "best_match_score": round(score, 4),
                        "rationale": entry["rationale"],
                        "suggested_clause_text": entry["typical_text"],
                    }
                )

    summary = (
        f"Flagged {len(missing)} missing standard clause(s) out of "
        f"{len(catalog)} checked ({contract_type} contract)."
    )

    return {
        "contract_type": contract_type,
        "checked": len(catalog),
        "missing": missing,
        "present": present,
        "summary": summary,
    }
