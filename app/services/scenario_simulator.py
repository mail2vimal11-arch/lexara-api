"""
Post-signature clause scenario simulator.
Models what happens when a clause is triggered, breached, or disputed.

Each scenario is built from a template that provides a structured timeline
of events, then scaled to the actual contract value from session_data. The
LLM generates a plain-English prevention summary that ties the jurisprudence
and the scenario together for the user.
"""

import httpx
import json
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# ---------------------------------------------------------------------------
# Jurisprudence database
# ---------------------------------------------------------------------------

JURISPRUDENCE_BY_CLAUSE: dict[str, list[dict]] = {
    "liability": [
        {
            "case_name": "Tercon Contractors Ltd v British Columbia (Transportation and Highways)",
            "citation": "2010 SCC 4",
            "court_or_tribunal": "Supreme Court of Canada",
            "year": 2010,
            "principle": (
                "Exclusion clauses, including limitation of liability clauses, are enforceable "
                "in commercial contracts when: (a) the clause is clear and unambiguous, "
                "(b) the clause was not unconscionable at the time of contracting, and "
                "(c) there is no overriding public policy reason to void it."
            ),
            "relevance_to_procurement": (
                "Sets the definitive Canadian test for enforcing LOL clauses in government and "
                "commercial procurement contracts. Courts will enforce well-drafted LOL caps."
            ),
        },
        {
            "case_name": "Hunter Engineering Co v Syncrude Canada Ltd",
            "citation": "[1989] 1 SCR 426",
            "court_or_tribunal": "Supreme Court of Canada",
            "year": 1989,
            "principle": (
                "Fundamental breach does not automatically void exclusion clauses. "
                "The clause must be interpreted in context; if it was intended to apply to "
                "the breach that occurred, it will be enforced."
            ),
            "relevance_to_procurement": (
                "Even in cases of serious contractor failure, properly drafted LOL clauses "
                "remain enforceable in Canadian procurement contracts."
            ),
        },
    ],
    "ip_ownership": [
        {
            "case_name": "Cdn Taxpayers Federation v Ontario (Minister of Finance)",
            "citation": "2004 CanLII 4005 (ON CA)",
            "court_or_tribunal": "Ontario Court of Appeal",
            "year": 2004,
            "principle": (
                "Crown IP vesting provisions must be explicitly stated in the contract. "
                "In the absence of clear IP assignment language, copyright vests with the "
                "creator (contractor) under the Copyright Act."
            ),
            "relevance_to_procurement": (
                "Government contracts without explicit Crown IP vesting clauses result in "
                "the vendor retaining copyright. This is a critical gap in many Ontario "
                "public sector contracts."
            ),
        },
    ],
    "termination": [
        {
            "case_name": "Bhasin v Hrynew",
            "citation": "2014 SCC 71",
            "court_or_tribunal": "Supreme Court of Canada",
            "year": 2014,
            "principle": (
                "There is a general organizing principle of good faith in Canadian contract "
                "law. Parties must not exercise contractual discretion (including termination "
                "rights) in a manner that is dishonest or that violates reasonable contractual "
                "expectations."
            ),
            "relevance_to_procurement": (
                "Termination for convenience clauses in procurement contracts must be exercised "
                "in good faith. Arbitrary or bad-faith termination may expose the Crown to "
                "damages beyond the contract's termination payment provisions."
            ),
        },
    ],
    "payment_terms": [
        {
            "case_name": "Prompt Payment Act (Ontario)",
            "citation": "SO 2019, c 13, Sched 5",
            "court_or_tribunal": "Ontario Legislature",
            "year": 2019,
            "principle": (
                "Ontario's Prompt Payment Act requires payment within 28 days of a proper "
                "invoice for construction contracts. Non-payment triggers adjudication rights "
                "under the Act."
            ),
            "relevance_to_procurement": (
                "Ontario construction contracts must comply with Prompt Payment Act timelines. "
                "Contract terms purporting to extend payment beyond 28 days for construction "
                "work may be unenforceable."
            ),
        },
    ],
    "sla": [
        {
            "case_name": "MDS Inc v Factory Mutual Insurance Co",
            "citation": "2021 ONCA 594",
            "court_or_tribunal": "Ontario Court of Appeal",
            "year": 2021,
            "principle": (
                "SLA performance credits are liquidated damages provisions. They will be "
                "enforced as written unless they constitute a penalty (grossly disproportionate "
                "to the loss). A well-calibrated credit schedule that approximates actual loss "
                "is enforceable."
            ),
            "relevance_to_procurement": (
                "Service credit schedules in IT and services contracts are enforceable in "
                "Ontario when the credit rate reflects a genuine pre-estimate of damages from "
                "service degradation."
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# Scenario templates
# ---------------------------------------------------------------------------

# Timeline events are expressed as fractions of contract_value_cad:
#   financial_exposure_min = contract_value * min_factor
#   financial_exposure_max = contract_value * max_factor
# A factor of 0 means no direct financial exposure from this event alone.

SCENARIO_TEMPLATES: dict[str, dict[str, list[dict]]] = {
    "liability": {
        "breach": [
            {
                "day": 1,
                "event": "Contractor delivers defective software deliverable; buyer identifies material non-conformance.",
                "min_factor": 0.0,
                "max_factor": 0.02,
                "legal_obligation": "Buyer must provide written notice of defect within the cure period specified in the contract.",
                "risk_factor": "Absence of a defined acceptance testing period allows contractor to dispute whether a defect exists.",
                "can_be_mitigated_by": "Explicit acceptance criteria clause with objective pass/fail metrics.",
            },
            {
                "day": 30,
                "event": "Cure period expires; contractor has not remediated the defect. Buyer escalates to formal dispute.",
                "min_factor": 0.05,
                "max_factor": 0.15,
                "legal_obligation": "Buyer must mitigate losses; failure to mitigate reduces recoverable damages under Canadian common law.",
                "risk_factor": "No limitation of liability clause means uncapped exposure for the contractor.",
                "can_be_mitigated_by": "Mutual LOL cap at 12 months contract value, consistent with Ontario IT contract standard.",
            },
            {
                "day": 90,
                "event": "Buyer retains replacement vendor. Replacement and transition costs are incurred.",
                "min_factor": 0.15,
                "max_factor": 0.35,
                "legal_obligation": "Buyer can claim direct damages including re-procurement costs. Consequential damages require explicit contract provision or statutory basis.",
                "risk_factor": "Without LOL clause, contractor faces claims for lost business opportunity, reputational harm, and third-party losses.",
                "can_be_mitigated_by": "Consequential damages exclusion clause combined with a defined direct-damages cap.",
            },
            {
                "day": 180,
                "event": "Dispute proceeds to arbitration or Ontario Superior Court litigation.",
                "min_factor": 0.10,
                "max_factor": 0.25,
                "legal_obligation": "Both parties bear legal costs unless the contract allocates costs differently or the court awards them.",
                "risk_factor": "Prolonged litigation increases reputational and financial exposure beyond the original defect.",
                "can_be_mitigated_by": "Mandatory mediation clause before arbitration or litigation, with defined cost-sharing.",
            },
        ],
        "enforcement": [
            {
                "day": 1,
                "event": "Buyer invokes LOL cap after contractor breach.",
                "min_factor": 0.0,
                "max_factor": 0.0,
                "legal_obligation": "Buyer must demonstrate the loss falls within the scope of recoverable damages under the LOL clause.",
                "risk_factor": "Poorly drafted LOL cap may exclude the buyer's primary head of loss.",
                "can_be_mitigated_by": "LOL clause that explicitly lists covered damage categories (direct loss, re-procurement, transition).",
            },
            {
                "day": 45,
                "event": "Contractor contests enforceability of LOL clause, citing fundamental breach (Syncrude/Hunter test).",
                "min_factor": 0.03,
                "max_factor": 0.12,
                "legal_obligation": "Courts apply the Tercon test: was the clause clear? Was it unconscionable at contracting?",
                "risk_factor": "Ambiguous LOL drafting creates litigation risk even when both parties intended the clause to apply.",
                "can_be_mitigated_by": "Clear, unambiguous LOL clause that explicitly applies to all breaches including fundamental breach.",
            },
        ],
        "worst_case": [
            {
                "day": 1,
                "event": "No LOL clause in contract. Contractor causes system-wide outage affecting buyer's operations.",
                "min_factor": 0.20,
                "max_factor": 0.80,
                "legal_obligation": "Contractor exposed to full consequential and direct damages with no contractual ceiling.",
                "risk_factor": "For a government buyer, downstream public service impacts can dramatically inflate the damages claim.",
                "can_be_mitigated_by": "Bilateral LOL cap negotiated at contract execution; carve-outs for gross negligence and willful misconduct only.",
            },
        ],
    },
    "termination": {
        "breach": [
            {
                "day": 1,
                "event": "Buyer terminates contract for cause alleging material breach.",
                "min_factor": 0.0,
                "max_factor": 0.05,
                "legal_obligation": "Buyer must demonstrate a 'material breach'; minor deficiencies do not trigger a for-cause termination right.",
                "risk_factor": "Overly broad 'material breach' definition allows the buyer to terminate for trivial non-performance.",
                "can_be_mitigated_by": "Explicit materiality threshold and minimum cure period (30 days) in the termination clause.",
            },
            {
                "day": 15,
                "event": "Contractor disputes characterization of breach; operations continue under protest.",
                "min_factor": 0.02,
                "max_factor": 0.08,
                "legal_obligation": "Under Bhasin v Hrynew, termination must be exercised in good faith and not to opportunistically strip the contractor of earned benefits.",
                "risk_factor": "Termination timing (e.g., just before milestone payment) may attract bad-faith damages.",
                "can_be_mitigated_by": "Good faith termination clause; payment of work-in-progress upon termination regardless of dispute.",
            },
            {
                "day": 60,
                "event": "Contractor makes claim for wrongful termination damages including lost profits.",
                "min_factor": 0.10,
                "max_factor": 0.40,
                "legal_obligation": "Wrongful termination triggers expectation damages — the value of the remaining contract the contractor would have performed.",
                "risk_factor": "Multi-year contracts with large unperformed value expose the buyer to substantial lost-profits claims.",
                "can_be_mitigated_by": "Termination for convenience clause with defined compensation formula (work performed + committed costs + limited profit margin).",
            },
        ],
        "enforcement": [
            {
                "day": 1,
                "event": "Buyer exercises termination for convenience. Contract work stops.",
                "min_factor": 0.0,
                "max_factor": 0.02,
                "legal_obligation": "Buyer must pay all work performed to termination date; committed third-party costs; and (if agreed) a termination fee.",
                "risk_factor": "Absent a defined convenience termination formula, quantum is disputed and determined by court or arbitrator.",
                "can_be_mitigated_by": "Pre-agreed termination for convenience payment schedule covering work in progress, committed costs, and reasonable profit.",
            },
        ],
        "worst_case": [
            {
                "day": 1,
                "event": "No termination clause. Buyer attempts to walk away from a multi-year services contract.",
                "min_factor": 0.30,
                "max_factor": 0.70,
                "legal_obligation": "Without a termination clause, buyer faces common law damages for all reasonably foreseeable losses including lost profits for the entire remaining term.",
                "risk_factor": "Large IT services or managed services contracts can result in tens of millions in lost-profit claims.",
                "can_be_mitigated_by": "Termination for convenience clause with compensation capped at work performed plus committed costs.",
            },
        ],
    },
    "ip_ownership": {
        "breach": [
            {
                "day": 1,
                "event": "Contract completes. Buyer attempts to modify or re-use deliverables. Vendor asserts copyright ownership.",
                "min_factor": 0.0,
                "max_factor": 0.05,
                "legal_obligation": (
                    "Under the Copyright Act (Canada), copyright vests with the author at creation "
                    "unless there is a written assignment. Employment exception does not apply to contractors."
                ),
                "risk_factor": "Many Canadian public sector contracts omit explicit IP assignment language.",
                "can_be_mitigated_by": "Explicit Crown IP vesting clause or broad perpetual licence in favour of the buyer.",
            },
            {
                "day": 90,
                "event": "Buyer modifies deliverables for a new project; vendor issues cease-and-desist.",
                "min_factor": 0.05,
                "max_factor": 0.20,
                "legal_obligation": "Modifying a copyright work without authority constitutes infringement (Copyright Act, s. 27).",
                "risk_factor": "Government buyer may have deployed the deliverables across multiple departments — systemic infringement risk.",
                "can_be_mitigated_by": "IP ownership vesting in Crown on payment, or a broad unrestricted licence including right to modify.",
            },
            {
                "day": 180,
                "event": "Federal Court action for copyright infringement and injunction.",
                "min_factor": 0.10,
                "max_factor": 0.40,
                "legal_obligation": "Plaintiff can seek statutory damages of $500–$20,000 per work infringed (Copyright Act, s. 38.1), plus injunction.",
                "risk_factor": "Multiple deliverables = multiple works = multiplicative statutory damages exposure.",
                "can_be_mitigated_by": "Clause vesting all deliverables, including intermediate and derivative works, in the buyer on payment.",
            },
        ],
        "enforcement": [
            {
                "day": 1,
                "event": "Government invokes Crown IP vesting clause; vendor disputes it applies to pre-existing background IP.",
                "min_factor": 0.0,
                "max_factor": 0.10,
                "legal_obligation": "Crown IP vesting clause must clearly distinguish foreground IP (created under the contract) from background IP (pre-existing).",
                "risk_factor": "Overly broad IP assignment may capture vendor's pre-existing tools and platform, exposing buyer to warranty breach claim.",
                "can_be_mitigated_by": "Clear foreground/background IP split; background IP retained by vendor with licence to buyer for use in deliverables.",
            },
        ],
        "worst_case": [
            {
                "day": 1,
                "event": "No IP clause. Vendor sells 'identical' system to a competing organization.",
                "min_factor": 0.25,
                "max_factor": 0.60,
                "legal_obligation": "Without IP ownership, buyer has no legal recourse against vendor re-selling substantially similar work.",
                "risk_factor": "For bespoke government systems, competitive intelligence embedded in the deliverable can be sold to competitors or adversaries.",
                "can_be_mitigated_by": "Crown IP vesting on all foreground IP plus a non-compete restriction on the same deliverable type.",
            },
        ],
    },
    "payment_terms": {
        "breach": [
            {
                "day": 1,
                "event": "Vendor submits invoice. Buyer fails to pay within contractual payment period.",
                "min_factor": 0.0,
                "max_factor": 0.01,
                "legal_obligation": "Vendor is entitled to interest on overdue amounts; Ontario construction contracts must comply with Prompt Payment Act (SO 2019).",
                "risk_factor": "Vague 'net 60' or 'net 90' payment terms leave vendor carrying working capital costs.",
                "can_be_mitigated_by": "Net 30 payment terms with automatic interest at Bank of Canada rate plus 2% on overdue amounts.",
            },
            {
                "day": 45,
                "event": "Vendor suspends performance citing non-payment.",
                "min_factor": 0.05,
                "max_factor": 0.15,
                "legal_obligation": "Vendor right to suspend performance requires clear contractual basis; common law right to suspend for repudiation is narrower.",
                "risk_factor": "Suspension of IT services mid-project can cause irreversible project delays and cascading costs.",
                "can_be_mitigated_by": "Explicit right to suspend with 14-day advance notice; buyer step-in rights to avoid service interruption.",
            },
        ],
        "enforcement": [
            {
                "day": 1,
                "event": "Vendor invokes prompt payment adjudication under Ontario Prompt Payment Act.",
                "min_factor": 0.0,
                "max_factor": 0.03,
                "legal_obligation": "Ontario's Construction Act requires an adjudicator's decision within 30 days of appointment; decision is binding pending appeal.",
                "risk_factor": "Prompt payment adjudication applies only to 'construction' contracts as defined in the Act — IT services may not qualify.",
                "can_be_mitigated_by": "Contractual adjudication clause mirroring Prompt Payment Act regardless of whether the Act applies by statute.",
            },
        ],
        "worst_case": [
            {
                "day": 1,
                "event": "Buyer becomes insolvent mid-contract; vendor is an unsecured creditor for unpaid invoices.",
                "min_factor": 0.20,
                "max_factor": 0.50,
                "legal_obligation": "In insolvency, unsecured creditors receive cents on the dollar after secured creditors and preferred creditors.",
                "risk_factor": "Large milestone-based contracts create concentration risk — vendor may have significant work in progress with no payment received.",
                "can_be_mitigated_by": "Milestone payment schedule with frequent invoicing; retention amount no greater than 5% of contract value.",
            },
        ],
    },
    "sla": {
        "breach": [
            {
                "day": 1,
                "event": "IT system experiences unplanned outage exceeding SLA uptime threshold.",
                "min_factor": 0.0,
                "max_factor": 0.02,
                "legal_obligation": "Service credits, if any, are the contractual remedy for SLA breach. They typically represent liquidated damages.",
                "risk_factor": "SLA without service credits leaves the buyer with only common law damages — harder to prove and quantify.",
                "can_be_mitigated_by": "Tiered service credit schedule with automatic credits for each breach level (e.g., 99.9% vs 99.5% uptime).",
            },
            {
                "day": 30,
                "event": "Repeated SLA breaches over a calendar month trigger termination right.",
                "min_factor": 0.03,
                "max_factor": 0.10,
                "legal_obligation": "Buyer may terminate for cause if SLA breaches meet the contractual materiality threshold.",
                "risk_factor": "No defined materiality threshold means buyer and vendor will dispute whether cumulative breaches justify termination.",
                "can_be_mitigated_by": "Explicit 'chronic breach' termination trigger: e.g., 3 or more SLA breaches in any rolling 90-day period.",
            },
            {
                "day": 90,
                "event": "Buyer claims consequential losses from downtime (lost revenue, regulatory penalty).",
                "min_factor": 0.10,
                "max_factor": 0.35,
                "legal_obligation": "Service credits are generally the exclusive remedy for SLA breach unless the contract expressly preserves additional remedies.",
                "risk_factor": "Credits-as-exclusive-remedy clauses may prevent the buyer from recovering actual business loss from a major outage.",
                "can_be_mitigated_by": "Carve-out from exclusive remedy clause for gross negligence, willful misconduct, or outages exceeding a defined severity threshold.",
            },
        ],
        "enforcement": [
            {
                "day": 1,
                "event": "Vendor contests measurement methodology for SLA breach — disputes whether downtime clock started correctly.",
                "min_factor": 0.0,
                "max_factor": 0.05,
                "legal_obligation": "The party alleging SLA breach bears the burden of demonstrating non-conformance using the contractually defined measurement methodology.",
                "risk_factor": "Ambiguous SLA measurement definitions create disputes over every marginal breach.",
                "can_be_mitigated_by": "SLA clause with objective measurement definition, agreed monitoring tool, and dispute resolution mechanism for measurement disputes.",
            },
        ],
        "worst_case": [
            {
                "day": 1,
                "event": "No SLA clause. Mission-critical government system is unavailable for 72 hours.",
                "min_factor": 0.15,
                "max_factor": 0.45,
                "legal_obligation": "Without SLA, buyer must prove damages at common law — must show causation, loss, and that loss was not too remote.",
                "risk_factor": "Government systems have downstream public service impacts that may be difficult to quantify and may be dismissed as too remote.",
                "can_be_mitigated_by": "SLA with uptime guarantees, service credits, and explicit right to claim direct consequential losses from defined critical failures.",
            },
        ],
    },
    "acceptance_criteria": {
        "breach": [
            {
                "day": 1,
                "event": "Vendor delivers project milestone. Buyer refuses to accept without clear criteria.",
                "min_factor": 0.0,
                "max_factor": 0.03,
                "legal_obligation": "Without objective acceptance criteria, acceptance is a matter of reasonable satisfaction — a subjective test courts apply with caution.",
                "risk_factor": "Absence of criteria allows the buyer to reject conforming deliverables, triggering a payment dispute.",
                "can_be_mitigated_by": "Objective acceptance test matrix: defined test cases, pass/fail thresholds, and deemed-acceptance after 10 business days without notice of rejection.",
            },
            {
                "day": 30,
                "event": "Acceptance dispute escalates; vendor claims deemed acceptance; buyer claims ongoing deficiencies.",
                "min_factor": 0.05,
                "max_factor": 0.15,
                "legal_obligation": "Vendor may argue deemed acceptance if the buyer continued to use the deliverable without issuing a formal rejection notice.",
                "risk_factor": "Continued operational use of a deliverable may constitute acceptance even if defects remain.",
                "can_be_mitigated_by": "Explicit 'no deemed acceptance by use' clause; acceptance requires a formal written sign-off.",
            },
        ],
        "enforcement": [
            {
                "day": 1,
                "event": "Buyer applies acceptance criteria; deliverable fails 3 of 12 test cases.",
                "min_factor": 0.0,
                "max_factor": 0.04,
                "legal_obligation": "Vendor must remediate within the contractual cure period (typically 15-30 business days) and re-submit for acceptance testing.",
                "risk_factor": "Multiple re-test cycles consume buyer resources and delay project go-live.",
                "can_be_mitigated_by": "Acceptance clause capping re-test cycles at 2, after which the buyer may accept with a price reduction or terminate for cause.",
            },
        ],
        "worst_case": [
            {
                "day": 1,
                "event": "No acceptance criteria. Custom-built government system deployed but fails in production.",
                "min_factor": 0.20,
                "max_factor": 0.55,
                "legal_obligation": "Buyer has an implied fitness-for-purpose warranty under common law, but must prove the system was unfit at the time of delivery.",
                "risk_factor": "Post-deployment failures are harder to attribute to the contractor once the buyer has been using the system.",
                "can_be_mitigated_by": "Pre-deployment acceptance testing framework with defined defect severity levels and remediation timelines.",
            },
        ],
    },
}

# Probability of each scenario type occurring (base rates by clause type and scenario)
SCENARIO_BASE_PROBABILITIES: dict[str, dict[str, float]] = {
    "liability": {"breach": 0.18, "enforcement": 0.22, "worst_case": 0.08},
    "termination": {"breach": 0.14, "enforcement": 0.20, "worst_case": 0.06},
    "ip_ownership": {"breach": 0.12, "enforcement": 0.15, "worst_case": 0.05},
    "payment_terms": {"breach": 0.22, "enforcement": 0.18, "worst_case": 0.09},
    "sla": {"breach": 0.30, "enforcement": 0.25, "worst_case": 0.12},
    "acceptance_criteria": {"breach": 0.20, "enforcement": 0.16, "worst_case": 0.07},
}

# Risk severity multipliers on scenario probability
SEVERITY_PROBABILITY_MULTIPLIERS = {
    "critical": 1.6,
    "high": 1.3,
    "medium": 1.0,
    "low": 0.6,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _scale_timeline(
    template_events: list[dict], contract_value_cad: float
) -> tuple[list[dict], float, float]:
    """
    Scale template events by contract_value_cad and return the scaled timeline
    plus aggregated min/max financial exposure totals.
    """
    timeline = []
    total_min = 0.0
    total_max = 0.0

    for evt in template_events:
        min_exposure = round(evt["min_factor"] * contract_value_cad, 2)
        max_exposure = round(evt["max_factor"] * contract_value_cad, 2)
        total_min += min_exposure
        total_max += max_exposure
        timeline.append(
            {
                "day": evt["day"],
                "event": evt["event"],
                "financial_exposure_min": min_exposure,
                "financial_exposure_max": max_exposure,
                "legal_obligation": evt["legal_obligation"],
                "risk_factor": evt["risk_factor"],
                "can_be_mitigated_by": evt["can_be_mitigated_by"],
            }
        )

    return timeline, total_min, total_max


def _amendment_reduction_factor(scenario_type: str) -> tuple[float, float]:
    """
    Return (min_reduction, max_reduction) factors representing how much of the
    raw exposure is eliminated by having a well-drafted clause amendment.
    """
    # A good amendment does not eliminate 100% of risk — some residual exposure always remains.
    reductions = {
        "breach": (0.60, 0.75),
        "enforcement": (0.70, 0.85),
        "worst_case": (0.50, 0.70),
    }
    return reductions.get(scenario_type, (0.55, 0.70))


def _calculate_scenario_probability(
    clause_type: str, scenario_type: str, risk_severity: str
) -> float:
    """Compute probability of this scenario occurring, accounting for risk severity."""
    base = SCENARIO_BASE_PROBABILITIES.get(clause_type, {}).get(scenario_type, 0.10)
    multiplier = SEVERITY_PROBABILITY_MULTIPLIERS.get(risk_severity, 1.0)
    return round(min(0.95, base * multiplier), 3)


async def _generate_prevention_summary(
    clause_data: dict,
    scenario_type: str,
    session_data: dict,
    timeline: list[dict],
    total_exposure_max: float,
    exposure_with_amendment_max: float,
    jurisprudence: list[dict],
) -> str:
    """
    Generate a plain-English summary explaining what clause amendment prevents this scenario.
    Uses Groq → Claude waterfall.
    """
    clause_type = clause_data.get("clause_type", "contract")
    clause_key = clause_data.get("clause_key", "this clause")
    jurisdiction_code = session_data.get("jurisdiction_code", "ON")
    contract_value_cad = float(session_data.get("contract_value_cad") or 0)

    value_at_risk = total_exposure_max - exposure_with_amendment_max
    case_ref = jurisprudence[0]["citation"] if jurisprudence else "applicable Canadian case law"
    case_name = jurisprudence[0]["case_name"] if jurisprudence else ""

    # Key mitigation language from the last timeline event
    last_mitigation = timeline[-1]["can_be_mitigated_by"] if timeline else ""

    system_prompt = (
        "You are a senior Canadian commercial lawyer writing a plain-English risk summary "
        "for a non-lawyer procurement professional. "
        "Write in clear, direct language. Avoid Latin terms. "
        "Return only the summary text — no headings, no bullet points, no JSON."
    )

    user_prompt = (
        f"Explain to a procurement professional what would happen if this {scenario_type} scenario "
        f"occurred on the {clause_type.replace('_', ' ')} clause of a "
        f"${contract_value_cad:,.0f} CAD {jurisdiction_code} contract, "
        f"and what specific clause amendment would prevent it.\n\n"
        f"Scenario summary: {timeline[0]['event'] if timeline else 'clause triggered'}\n"
        f"Maximum financial exposure without amendment: ${total_exposure_max:,.0f} CAD\n"
        f"Maximum exposure with a well-drafted amendment: ${exposure_with_amendment_max:,.0f} CAD\n"
        f"Key mitigation: {last_mitigation}\n"
        f"Relevant case: {case_name} ({case_ref})\n\n"
        "Write 3-4 sentences explaining:\n"
        "1. What goes wrong in plain language\n"
        "2. How much it could cost\n"
        "3. What specific amendment language prevents this\n"
        "4. Why the cited case matters\n\n"
        "Return only the paragraph text. No bullet points, no JSON."
    )

    # Waterfall: Groq → Claude
    if settings.use_groq and settings.groq_api_key:
        try:
            text = await _call_groq_raw(system_prompt, user_prompt)
            logger.info(f"Scenario simulator: Groq prevention summary success")
            return text
        except Exception as e:
            logger.warning(f"Groq failed for prevention summary, falling back to Claude: {e}")

    try:
        text = await _call_claude_raw(system_prompt, user_prompt)
        logger.info(f"Scenario simulator: Claude prevention summary success")
        return text
    except Exception as e:
        logger.error(f"Claude also failed for prevention summary: {e}")
        # Graceful fallback
        return (
            f"If this {scenario_type} scenario occurs on the "
            f"{clause_type.replace('_', ' ')} clause, the financial exposure could reach "
            f"${total_exposure_max:,.0f} CAD. "
            f"A well-drafted amendment ({last_mitigation}) reduces this exposure to "
            f"approximately ${exposure_with_amendment_max:,.0f} CAD, saving "
            f"${value_at_risk:,.0f} CAD. "
            f"See {case_name} ({case_ref}) for the governing legal test in {jurisdiction_code}."
        )


async def _call_groq_raw(system_prompt: str, user_prompt: str) -> str:
    """Call Groq with free-form prompts. Raises on failure."""
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
        "max_tokens": 600,
        "temperature": 0.4,
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

    return choices[0]["message"]["content"].strip()


async def _call_claude_raw(system_prompt: str, user_prompt: str) -> str:
    """Call Claude with free-form prompts. Raises on failure."""
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
                "max_tokens": 600,
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def simulate_scenario(
    clause_data: dict,
    scenario_type: str,
    session_data: dict,
) -> dict:
    """
    Run a post-signature scenario simulation for a specific clause and scenario type.

    Parameters
    ----------
    clause_data : dict
        Keys: clause_key, clause_type, risk_severity, original_text,
              your_proposed_text (the amendment, if any)
    scenario_type : str
        One of: "breach" | "enforcement" | "worst_case"
    session_data : dict
        Keys: contract_value_cad, jurisdiction_code

    Returns
    -------
    dict
        scenario_type               : str
        clause_key                  : str
        timeline                    : list[dict]
        total_exposure_min_cad      : float
        total_exposure_max_cad      : float
        exposure_with_amendment_min_cad : float
        exposure_with_amendment_max_cad : float
        value_of_clause_amendment_cad   : float
        jurisprudence_references    : list[dict]
        prevention_summary          : str
        probability_of_scenario     : float
    """
    clause_type = clause_data.get("clause_type", "")
    clause_key = clause_data.get("clause_key", "unknown")
    risk_severity = clause_data.get("risk_severity", "medium")
    contract_value_cad = float(session_data.get("contract_value_cad") or 1_000_000)

    # ── Resolve template ──────────────────────────────────────────────────────
    clause_templates = SCENARIO_TEMPLATES.get(clause_type, {})
    if not clause_templates:
        logger.warning(
            f"No scenario template for clause_type={clause_type!r}; "
            f"using liability template as fallback."
        )
        clause_templates = SCENARIO_TEMPLATES["liability"]

    # Validate scenario_type; default to "breach"
    if scenario_type not in clause_templates:
        logger.warning(
            f"scenario_type={scenario_type!r} not found for clause_type={clause_type!r}; "
            f"defaulting to 'breach'."
        )
        scenario_type = "breach"
        if scenario_type not in clause_templates:
            scenario_type = next(iter(clause_templates))

    template_events = clause_templates[scenario_type]

    # ── Scale timeline ────────────────────────────────────────────────────────
    timeline, total_min, total_max = _scale_timeline(template_events, contract_value_cad)

    # ── Amendment exposure ────────────────────────────────────────────────────
    min_red, max_red = _amendment_reduction_factor(scenario_type)
    exposure_with_amendment_min = round(total_min * (1.0 - max_red), 2)
    exposure_with_amendment_max = round(total_max * (1.0 - min_red), 2)
    value_of_amendment = round(total_max - exposure_with_amendment_max, 2)

    # ── Jurisprudence ─────────────────────────────────────────────────────────
    jurisprudence = JURISPRUDENCE_BY_CLAUSE.get(clause_type, [])
    # Include generic SCC good-faith principle for all contract clauses
    if not jurisprudence:
        jurisprudence = JURISPRUDENCE_BY_CLAUSE.get("termination", [])

    # ── Scenario probability ──────────────────────────────────────────────────
    probability = _calculate_scenario_probability(clause_type, scenario_type, risk_severity)

    # ── Prevention summary via LLM ────────────────────────────────────────────
    prevention_summary = await _generate_prevention_summary(
        clause_data=clause_data,
        scenario_type=scenario_type,
        session_data=session_data,
        timeline=timeline,
        total_exposure_max=total_max,
        exposure_with_amendment_max=exposure_with_amendment_max,
        jurisprudence=jurisprudence,
    )

    return {
        "scenario_type": scenario_type,
        "clause_key": clause_key,
        "timeline": timeline,
        "total_exposure_min_cad": total_min,
        "total_exposure_max_cad": total_max,
        "exposure_with_amendment_min_cad": exposure_with_amendment_min,
        "exposure_with_amendment_max_cad": exposure_with_amendment_max,
        "value_of_clause_amendment_cad": value_of_amendment,
        "jurisprudence_references": jurisprudence,
        "prevention_summary": prevention_summary,
        "probability_of_scenario": probability,
    }
