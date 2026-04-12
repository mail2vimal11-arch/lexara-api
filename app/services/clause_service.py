"""
clause_library.py — SACC-style Standard Clause Repository
Mock JSON database of standard Canadian procurement clauses.
Inspired by PWGSC SACC Manual, Bonterms, and CommonAccord.
"""

import re
from typing import Optional

# ── Clause Database ───────────────────────────────────────────────────────────
# Each clause has:
#   id:           unique identifier (SACC-style)
#   category:     broad grouping
#   title:        display name
#   tags:         searchable keywords
#   text:         standard clause text
#   source:       reference (SACC, custom, etc.)
#   notes:        drafter notes

CLAUSE_DB: list[dict] = [
    {
        "id": "GEN-001",
        "category": "General",
        "title": "Entire Agreement",
        "tags": ["entire agreement", "integration", "merger"],
        "text": (
            "This Contract constitutes the entire agreement between the parties with respect to its "
            "subject matter and supersedes all prior negotiations, representations, warranties, "
            "understandings, and agreements, whether written or oral, between the parties relating "
            "to the subject matter of this Contract."
        ),
        "source": "Custom / Best Practice",
        "notes": "Include after all schedules are listed. Prevents reliance on pre-contract representations.",
    },
    {
        "id": "GEN-002",
        "category": "General",
        "title": "Governing Law",
        "tags": ["governing law", "jurisdiction", "ontario", "canada"],
        "text": (
            "This Contract shall be governed by and construed in accordance with the laws of the "
            "Province of Ontario and the federal laws of Canada applicable therein. Each party "
            "irrevocably attoms to the exclusive jurisdiction of the courts of Ontario."
        ),
        "source": "Custom / Best Practice",
        "notes": "Adjust province as required. For federal Crown contracts, federal jurisdiction typically applies.",
    },
    {
        "id": "INDEM-001",
        "category": "Indemnification",
        "title": "Contractor Indemnification (Standard)",
        "tags": ["indemnification", "indemnity", "liability", "hold harmless"],
        "text": (
            "The Contractor shall indemnify and hold harmless Canada, its officers, employees, and "
            "agents (collectively, the 'Indemnified Parties') from and against any and all claims, "
            "damages, losses, costs, and expenses (including reasonable legal fees) arising out of or "
            "relating to: (a) any breach by the Contractor of this Contract; (b) any negligent or "
            "wrongful act or omission of the Contractor or its subcontractors; or (c) any infringement "
            "of intellectual property rights by the Contractor in the performance of this Contract."
        ),
        "source": "SACC Manual — Adapted",
        "notes": "Mutual indemnification may be appropriate for equal-risk commercial contracts.",
    },
    {
        "id": "INDEM-002",
        "category": "Indemnification",
        "title": "IP Indemnification",
        "tags": ["indemnification", "intellectual property", "ip", "infringement", "copyright", "patent"],
        "text": (
            "The Contractor shall defend, indemnify, and hold harmless the Indemnified Parties from any "
            "third-party claim alleging that the Deliverables, or Canada's use thereof as contemplated "
            "under this Contract, infringe any patent, copyright, trademark, trade secret, or other "
            "intellectual property right. The Contractor's obligation under this clause is conditional "
            "on Canada: (a) promptly notifying the Contractor in writing of the claim; (b) granting the "
            "Contractor sole control of the defence and settlement; and (c) providing reasonable assistance."
        ),
        "source": "Custom / Best Practice",
        "notes": "Ensure the Contractor has appropriate insurance to back this obligation.",
    },
    {
        "id": "LIAB-001",
        "category": "Limitation of Liability",
        "title": "Mutual Limitation of Liability",
        "tags": ["limitation of liability", "cap", "damages", "consequential", "indirect"],
        "text": (
            "Neither party shall be liable to the other for any indirect, incidental, special, "
            "exemplary, or consequential damages, including loss of revenue, loss of profits, "
            "loss of data, or loss of goodwill, even if advised of the possibility of such damages. "
            "Each party's aggregate liability arising out of or related to this Contract shall not "
            "exceed the total fees paid or payable by Canada to the Contractor in the twelve (12) "
            "months immediately preceding the event giving rise to the claim."
        ),
        "source": "Bonterms-Inspired / Best Practice",
        "notes": "Carve out fraud, gross negligence, wilful misconduct, and IP indemnification obligations from the cap.",
    },
    {
        "id": "LIAB-002",
        "category": "Limitation of Liability",
        "title": "Liability Cap Carve-Outs",
        "tags": ["limitation of liability", "carve out", "fraud", "gross negligence", "wilful misconduct"],
        "text": (
            "Notwithstanding the foregoing, the limitations on liability set out in this section shall "
            "not apply to: (a) a party's fraud or wilful misconduct; (b) a party's gross negligence; "
            "(c) a party's indemnification obligations under this Contract; (d) a party's obligations "
            "of confidentiality; or (e) any liability that cannot be limited by applicable law."
        ),
        "source": "Custom / Best Practice",
        "notes": "Pair with LIAB-001. Review with counsel for Crown liability considerations.",
    },
    {
        "id": "CONF-001",
        "category": "Confidentiality",
        "title": "Standard Confidentiality Obligation",
        "tags": ["confidentiality", "nda", "non-disclosure", "proprietary", "trade secret"],
        "text": (
            "Each party (as 'Receiving Party') agrees to: (a) hold in strict confidence all "
            "Confidential Information of the other party (the 'Disclosing Party'); (b) not disclose "
            "Confidential Information to any third party without the prior written consent of the "
            "Disclosing Party; and (c) use Confidential Information solely for the purposes of "
            "performing its obligations under this Contract. 'Confidential Information' means any "
            "information disclosed by a party that is designated as confidential or that reasonably "
            "should be understood to be confidential given the nature of the information and circumstances "
            "of disclosure, but excludes information that: (i) is or becomes publicly available without "
            "breach of this Contract; (ii) was rightfully known before disclosure; (iii) is rightfully "
            "obtained from a third party without restriction; or (iv) is independently developed."
        ),
        "source": "Custom / Best Practice",
        "notes": (
            "For Crown contracts, also reference the Security of Information Act, RSC 1985, c O-5 "
            "and applicable Treasury Board security standards."
        ),
    },
    {
        "id": "TERM-001",
        "category": "Termination",
        "title": "Termination for Convenience (Crown)",
        "tags": ["termination", "termination for convenience", "crown", "cancellation"],
        "text": (
            "Canada may, at any time, terminate this Contract for convenience by giving written notice "
            "to the Contractor. Upon receipt of such notice, the Contractor shall immediately cease work, "
            "except as necessary to preserve and protect work already performed. Canada's liability upon "
            "termination for convenience is limited to payment for work satisfactorily performed and "
            "accepted prior to the date of termination, together with reasonable and substantiated "
            "wind-down costs, not to exceed the unpaid Contract value."
        ),
        "source": "SACC Manual — Adapted (GC Std Clauses)",
        "notes": "Standard in all Crown procurement contracts. No obligation to pay lost profits.",
    },
    {
        "id": "TERM-002",
        "category": "Termination",
        "title": "Termination for Default",
        "tags": ["termination", "default", "breach", "cure period"],
        "text": (
            "Canada may terminate this Contract for default if the Contractor: (a) fails to perform "
            "any material obligation under this Contract and does not cure such failure within fifteen "
            "(15) business days after written notice from Canada specifying the nature of the default; "
            "(b) becomes insolvent, makes an assignment for the benefit of creditors, or is subject to "
            "bankruptcy or insolvency proceedings; or (c) is convicted of a criminal offence under the "
            "Integrity Provisions applicable to this Contract. Upon termination for default, Canada "
            "reserves all rights and remedies available at law and in equity."
        ),
        "source": "Custom / Best Practice",
        "notes": "Reference the Ineligibility and Suspension Policy (Integrity Framework) where applicable.",
    },
    {
        "id": "IP-001",
        "category": "Intellectual Property",
        "title": "Crown Ownership of Foreground IP",
        "tags": ["intellectual property", "ip", "crown ownership", "foreground ip", "deliverables"],
        "text": (
            "All intellectual property rights in any work, invention, design, software, data, "
            "documentation, or other material created, developed, or first reduced to practice by "
            "the Contractor (or its subcontractors) in the performance of this Contract ('Foreground IP') "
            "shall vest in and be owned exclusively by Canada upon creation. The Contractor hereby "
            "assigns to Canada all right, title, and interest in Foreground IP and agrees to execute "
            "such further instruments as Canada may reasonably request to perfect such assignment."
        ),
        "source": "PSPC Standard IP Terms",
        "notes": (
            "Review against the Ownership of Intellectual Property Policy (Treasury Board). "
            "For ISED/NRC-funded R&D, contractor IP ownership may be preferred."
        ),
    },
    {
        "id": "IP-002",
        "category": "Intellectual Property",
        "title": "Contractor Background IP Licence",
        "tags": ["intellectual property", "background ip", "licence", "license", "pre-existing"],
        "text": (
            "The Contractor hereby grants to Canada a non-exclusive, irrevocable, royalty-free, "
            "worldwide licence to use, reproduce, modify, and distribute any pre-existing intellectual "
            "property of the Contractor ('Background IP') that is incorporated into or necessary for "
            "Canada to use the Deliverables for the purposes contemplated by this Contract."
        ),
        "source": "PSPC Standard IP Terms — Adapted",
        "notes": "Ensure Background IP is clearly identified in a Schedule to avoid disputes.",
    },
    {
        "id": "PIPEDA-001",
        "category": "Privacy",
        "title": "Personal Information Protection (PIPEDA)",
        "tags": ["privacy", "personal information", "pipeda", "data protection", "privacy act"],
        "text": (
            "The Contractor shall comply with the Personal Information Protection and Electronic "
            "Documents Act, SC 2000, c 5 ('PIPEDA') and, where applicable, the Privacy Act, RSC 1985, "
            "c P-21, in its collection, use, and disclosure of personal information in the performance "
            "of this Contract. The Contractor shall: (a) collect only the personal information necessary "
            "for the purposes of this Contract; (b) implement appropriate technical and organizational "
            "safeguards to protect personal information against unauthorized access, disclosure, or loss; "
            "and (c) promptly notify Canada of any privacy breach involving personal information collected "
            "under this Contract."
        ),
        "source": "Custom / Best Practice",
        "notes": "For federal government contracts, the Privacy Act applies to Crown institutions directly.",
    },
    {
        "id": "DISP-001",
        "category": "Dispute Resolution",
        "title": "Escalation and Arbitration",
        "tags": ["dispute resolution", "arbitration", "mediation", "escalation", "adr"],
        "text": (
            "In the event of any dispute, controversy, or claim arising out of or relating to this "
            "Contract, or the breach, termination, or invalidity thereof, the parties shall first "
            "attempt to resolve the dispute through good-faith negotiation between senior representatives "
            "of each party for a period of thirty (30) calendar days from the date one party provides "
            "written notice of the dispute. If the dispute is not resolved through negotiation, either "
            "party may refer the matter to binding arbitration under the Arbitration Act, 1991, SO 1991, "
            "c 17 (Ontario), or the federal Commercial Arbitration Act, RSC 1985, c 17 (2nd Supp), as "
            "applicable. Nothing in this section prevents a party from seeking urgent injunctive or "
            "equitable relief from a court of competent jurisdiction."
        ),
        "source": "Custom / Best Practice",
        "notes": "Crown contracts may not be arbitrable without statutory authority. Confirm with legal counsel.",
    },
    {
        "id": "SOW-001",
        "category": "Statement of Work",
        "title": "Deliverables and Acceptance",
        "tags": ["deliverables", "acceptance", "statement of work", "sow", "milestones"],
        "text": (
            "The Contractor shall deliver the Deliverables described in Schedule A (Statement of Work) "
            "by the dates set out therein. Canada shall have fifteen (15) business days following receipt "
            "of each Deliverable to review and either: (a) provide written acceptance; or (b) provide "
            "written notice of non-conformance specifying in reasonable detail the deficiencies. The "
            "Contractor shall cure all identified deficiencies within ten (10) business days. If Canada "
            "does not respond within the review period, the Deliverable shall be deemed accepted."
        ),
        "source": "Custom / Best Practice",
        "notes": "Adjust review and cure periods to reflect project complexity and risk.",
    },
    {
        "id": "PAY-001",
        "category": "Payment",
        "title": "Payment Terms",
        "tags": ["payment", "invoice", "net 30", "fees", "compensation"],
        "text": (
            "Canada shall pay undisputed invoices within thirty (30) calendar days of receipt of a "
            "properly rendered invoice. Invoices must include: the Contract number, a description of "
            "work performed, the period covered, and HST/GST registration number. Late payments shall "
            "accrue interest at the rate prescribed under the Interest and Administrative Charges "
            "Regulations, SOR/96-188, from the date payment was due."
        ),
        "source": "Financial Administration Act / Interest Regs",
        "notes": "The Interest and Administrative Charges Regulations set the Crown's late payment interest obligation.",
    },
    {
        "id": "FM-001",
        "category": "Force Majeure",
        "title": "Force Majeure (Pandemic Extended)",
        "tags": ["force majeure", "pandemic", "epidemic", "act of god", "unforeseeable"],
        "text": (
            "Neither party shall be liable for delay or failure to perform if caused by events beyond "
            "reasonable control, including acts of God, war, terrorism, fire, flood, earthquake, epidemic, "
            "pandemic, governmental action, or labour disputes. The affected party shall notify the other "
            "within five (5) business days and use commercially reasonable efforts to resume performance. "
            "If the Force Majeure Event continues for more than ninety (90) days, either party may terminate."
        ),
        "source": "Custom / Best Practice",
        "notes": "Post-COVID, pandemic/epidemic language is now standard. Review insurance coverage alignment.",
    },
    {
        "id": "ASSIGN-001",
        "category": "Assignment",
        "title": "No Assignment Without Consent",
        "tags": ["assignment", "transfer", "consent", "subcontract"],
        "text": (
            "The Contractor shall not assign this Contract or any part thereof without the prior written "
            "consent of Canada. Any assignment made without consent is void. Canada may assign its rights "
            "under this Contract to any federal department or agency without the Contractor's consent."
        ),
        "source": "SACC Manual — Adapted",
        "notes": "Standard in Crown procurement. Consider adding change-of-control trigger language.",
    },
    {
        "id": "INS-001",
        "category": "Insurance",
        "title": "Insurance Requirements (Comprehensive)",
        "tags": ["insurance", "CGL", "professional liability", "cyber", "workers compensation"],
        "text": (
            "The Contractor shall maintain: (a) Commercial General Liability insurance of not less than "
            "$5,000,000 per occurrence; (b) Professional Liability (E&O) insurance of not less than "
            "$2,000,000 per claim; (c) Cyber Liability insurance of not less than $1,000,000; and "
            "(d) Workers' Compensation as required by law. Canada shall be named as additional insured "
            "on CGL. Certificates of insurance shall be provided prior to commencing work."
        ),
        "source": "Custom / Best Practice",
        "notes": "Adjust limits based on contract value and risk. Cyber liability is increasingly standard for IT contracts.",
    },
    {
        "id": "SUB-001",
        "category": "Subcontracting",
        "title": "Subcontracting (Consent Required)",
        "tags": ["subcontracting", "subcontractor", "consent", "prime contractor"],
        "text": (
            "The Contractor shall not subcontract any part of the Work without the prior written consent "
            "of the Contracting Authority. The Contractor remains fully responsible for all subcontracted "
            "work as if performed directly. Subcontracting does not relieve the Contractor of any "
            "obligation under this Contract."
        ),
        "source": "SACC Manual — Adapted",
        "notes": "Identify key subcontractors in the bid. Consent should not be unreasonably withheld.",
    },
    {
        "id": "COI-001",
        "category": "Conflict of Interest",
        "title": "Conflict of Interest Disclosure",
        "tags": ["conflict of interest", "disclosure", "organizational", "bias"],
        "text": (
            "The Contractor shall not provide services where such services could give rise to a real, "
            "potential, or apparent conflict of interest. The Contractor shall promptly disclose any "
            "situation that may constitute a conflict and Canada shall determine the appropriate remedy. "
            "The Contractor shall not provide advice on matters in which it has a financial interest "
            "without full disclosure and written consent."
        ),
        "source": "Custom / Best Practice",
        "notes": "Particularly important for advisory/consulting contracts. Include organizational COI screening.",
    },
    {
        "id": "KEY-001",
        "category": "Key Personnel",
        "title": "Key Personnel Requirements",
        "tags": ["key personnel", "named resources", "replacement", "qualifications"],
        "text": (
            "The Contractor shall assign the key personnel identified in its proposal. No key personnel "
            "shall be removed or replaced without the prior written consent of the Technical Authority. "
            "Proposed replacements must possess equivalent or greater qualifications and experience. "
            "Failure to maintain acceptable key personnel may constitute grounds for termination."
        ),
        "source": "Custom / Best Practice",
        "notes": "List specific individuals and roles in the SOW. Include a staffing matrix in Schedule B.",
    },
    {
        "id": "AUDIT-001",
        "category": "Audit Rights",
        "title": "Crown Audit Rights (7 Years)",
        "tags": ["audit", "inspection", "records", "auditor general", "financial"],
        "text": (
            "The Contractor shall maintain complete records of all costs incurred under this Contract for "
            "seven (7) years after final payment. Canada, the Auditor General, and their representatives "
            "may inspect, audit, and copy such records on reasonable notice. The Contractor shall provide "
            "all assistance and access necessary for audit purposes."
        ),
        "source": "Financial Administration Act / SACC",
        "notes": "Seven years is the standard retention period. Required for all cost-reimbursable contracts.",
    },
    {
        "id": "WARR-001",
        "category": "Warranty",
        "title": "Standard 12-Month Warranty",
        "tags": ["warranty", "defects", "guarantee", "repair", "replace"],
        "text": (
            "The Contractor warrants that all deliverables shall be free from defects in design, materials, "
            "and workmanship for twelve (12) months from written acceptance. During the warranty period, the "
            "Contractor shall repair or replace defective deliverables within ten (10) business days at no "
            "additional cost. The warranty shall not apply to defects caused by Canada's misuse."
        ),
        "source": "Custom / Best Practice",
        "notes": "Extend to 24 months for critical systems. Consider performance warranties for IT/software.",
    },
    {
        "id": "DATA-001",
        "category": "Data Residency",
        "title": "Canadian Data Residency",
        "tags": ["data residency", "data sovereignty", "canada", "cloud", "storage"],
        "text": (
            "All data, including personal information and Protected B information, shall be stored, "
            "processed, and backed up exclusively within Canada. The Contractor shall not transfer data "
            "outside Canada without prior written consent. Cloud infrastructure must be hosted in Canadian "
            "data centres operated by providers with a Canadian presence."
        ),
        "source": "TBS Directive on Service and Digital / Custom",
        "notes": "Mandatory for Protected B and above. Consider GC Cloud Guardrails compliance.",
    },
    {
        "id": "TRANS-001",
        "category": "Transition",
        "title": "Transition Services on Contract End",
        "tags": ["transition", "knowledge transfer", "handover", "successor", "exit"],
        "text": (
            "Upon expiry or termination, the Contractor shall provide transition services for up to ninety "
            "(90) days to facilitate orderly transfer to Canada or a successor. Transition shall include "
            "knowledge transfer, data migration, documentation of processes, and parallel operations support. "
            "The Contractor shall return or destroy all confidential information."
        ),
        "source": "Custom / Best Practice",
        "notes": "Critical for IT managed services and outsourcing. Include in pricing as a separate line.",
    },
    {
        "id": "BOND-001",
        "category": "Bonding",
        "title": "Bid Bond (10%)",
        "tags": ["bid bond", "surety", "financial security", "bid security"],
        "text": (
            "The Bidder shall provide a bid bond or irrevocable standby letter of credit equal to ten "
            "percent (10%) of the total bid price, issued by a surety licensed in Canada and acceptable "
            "to Canada. The bid bond shall remain valid for sixty (60) days following bid closing. "
            "The bond will be forfeited if the successful bidder fails to execute the contract."
        ),
        "source": "SACC Manual — Adapted",
        "notes": "Standard for construction contracts. Typically 10% of bid price. Treasury Board approved sureties.",
    },
    {
        "id": "BOND-002",
        "category": "Bonding",
        "title": "Performance Bond (50%)",
        "tags": ["performance bond", "surety", "financial security", "completion"],
        "text": (
            "Within fourteen (14) days of award, the Contractor shall deliver a performance bond equal to "
            "fifty percent (50%) of the Contract Price, issued by a Treasury Board approved surety. The "
            "bond shall remain in force until one year after substantial completion. The surety shall "
            "be jointly and severally liable with the Contractor for performance."
        ),
        "source": "SACC Manual — Adapted",
        "notes": "Pair with Labour and Material Bond. Standard for construction over $200K.",
    },
    {
        "id": "HOLD-001",
        "category": "Holdback",
        "title": "10% Holdback Until Substantial Completion",
        "tags": ["holdback", "retainage", "retention", "progress payment", "construction"],
        "text": (
            "Canada shall retain ten percent (10%) from each progress payment until Substantial Completion "
            "is certified. The holdback shall be released forty-five (45) days after Substantial Completion, "
            "provided all deficiency work is complete and no liens have been registered. The holdback "
            "complies with applicable provincial construction lien legislation."
        ),
        "source": "Construction Act / Best Practice",
        "notes": "Ontario Construction Act requires statutory holdback. Release timing follows lien expiry.",
    },
    {
        "id": "LANG-001",
        "category": "Official Languages",
        "title": "Bilingual Requirements",
        "tags": ["official languages", "bilingual", "english", "french", "translation"],
        "text": (
            "All deliverables, reports, user interfaces, and public-facing materials shall be provided in "
            "both official languages (English and French) in accordance with the Official Languages Act, "
            "RSC 1985, c 31 (4th Supp). Translation shall be of professional quality and reviewed by "
            "Canada's official languages coordinator."
        ),
        "source": "Official Languages Act / TBS Policy",
        "notes": "Mandatory for all federal public-facing deliverables. Budget for translation costs.",
    },
    {
        "id": "ENV-001",
        "category": "Environmental",
        "title": "Green Procurement Requirements",
        "tags": ["green procurement", "environmental", "sustainability", "carbon", "recycled"],
        "text": (
            "The Contractor shall comply with the Government of Canada's Policy on Green Procurement and "
            "the Federal Sustainable Development Strategy. Deliverables shall minimize environmental impact "
            "including use of recycled materials, energy-efficient equipment, and reduced packaging. The "
            "Contractor shall report on carbon footprint reduction measures quarterly."
        ),
        "source": "Policy on Green Procurement / FSDS",
        "notes": "Increasingly weighted in evaluation criteria. Consider LEED, Energy Star certifications.",
    },
    {
        "id": "SEC-001",
        "category": "Security",
        "title": "Personnel Security Clearance",
        "tags": ["security clearance", "reliability", "secret", "top secret", "CISD"],
        "text": (
            "Personnel requiring access to protected or classified information must hold a valid security "
            "clearance (Reliability Status, Secret, or Top Secret) issued by the Canadian Industrial "
            "Security Directorate. No individual shall access such information without the required "
            "clearance. The Contractor shall notify Canada immediately if any cleared person's status changes."
        ),
        "source": "PSPC Industrial Security / Custom",
        "notes": "Clearance levels: Reliability < Secret < Top Secret. Allow 3-6 months processing time.",
    },
    {
        "id": "ACCESS-001",
        "category": "Accessibility",
        "title": "WCAG 2.1 AA + AODA Compliance",
        "tags": ["accessibility", "WCAG", "AODA", "inclusive design", "assistive technology"],
        "text": (
            "All web-based deliverables and digital content shall meet WCAG 2.1 Level AA conformance and "
            "comply with the AODA Integrated Accessibility Standards, O Reg 191/11. The Contractor shall "
            "conduct accessibility testing with assistive technologies (screen readers, voice control) and "
            "provide a Voluntary Product Accessibility Template (VPAT) for all software deliverables."
        ),
        "source": "AODA / Accessible Canada Act / TBS Standard",
        "notes": "Mandatory for all Government of Canada web content. WCAG 2.1 AA is the minimum standard.",
    },
    {
        "id": "BC-001",
        "category": "Business Continuity",
        "title": "Business Continuity and Disaster Recovery",
        "tags": ["business continuity", "disaster recovery", "BCP", "DRP", "RTO", "RPO"],
        "text": (
            "The Contractor shall maintain a Business Continuity Plan and Disaster Recovery Plan ensuring "
            "recovery of critical services within four (4) hours (RTO) and data loss of no more than "
            "one (1) hour (RPO). Plans shall be tested annually with results provided to Canada. The "
            "Contractor shall notify Canada within one (1) hour of any service disruption."
        ),
        "source": "Custom / Best Practice",
        "notes": "Adjust RTO/RPO based on criticality. For Tier 1 systems, RTO may be 1 hour or less.",
    },
    {
        "id": "CORR-001",
        "category": "Anti-Corruption",
        "title": "Anti-Corruption (CFPOA Compliance)",
        "tags": ["anti-corruption", "bribery", "CFPOA", "integrity", "ethics"],
        "text": (
            "The Contractor certifies that neither the Contractor nor its agents have paid or offered any "
            "bribe or improper advantage to any public official in connection with this Contract, in "
            "violation of the Corruption of Foreign Public Officials Act, SC 1998, c 34, or the Criminal "
            "Code. The Contractor shall maintain an anti-corruption compliance program."
        ),
        "source": "CFPOA / Integrity Provisions",
        "notes": "Breach may result in ineligibility under the Ineligibility and Suspension Policy.",
    },
    {
        "id": "PRICE-001",
        "category": "Price Adjustment",
        "title": "Annual CPI Price Escalation",
        "tags": ["price adjustment", "escalation", "CPI", "inflation", "index"],
        "text": (
            "Contract rates shall be adjusted annually based on the Consumer Price Index (CPI) for Canada, "
            "All Items, as published by Statistics Canada. The adjustment equals the percentage change in "
            "CPI over the preceding twelve months, capped at three percent (3%) per year. Adjustments take "
            "effect on each anniversary of the contract effective date."
        ),
        "source": "Custom / Best Practice",
        "notes": "Use CANSIM Table 18-10-0004-01. Cap protects against runaway inflation.",
    },
    {
        "id": "LD-001",
        "category": "Liquidated Damages",
        "title": "Delay Damages (1% per week, 10% cap)",
        "tags": ["liquidated damages", "delay", "penalty", "late delivery"],
        "text": (
            "If the Contractor fails to deliver by the specified date, Canada is entitled to liquidated "
            "damages of one percent (1%) of the late deliverable value per week of delay, up to ten "
            "percent (10%) of total Contract Price. The parties agree this is a genuine pre-estimate "
            "of damages and not a penalty."
        ),
        "source": "Custom / Best Practice",
        "notes": "Must be a genuine pre-estimate — Canadian courts will strike penalty clauses. See Dunlop v New Garage.",
    },
    {
        "id": "SAAS-001",
        "category": "Cloud / SaaS",
        "title": "SaaS Service Terms",
        "tags": ["SaaS", "cloud", "subscription", "availability", "data portability", "exit"],
        "text": (
            "The Contractor shall deliver the SaaS solution with 99.9% availability measured monthly. "
            "Service credits of 2% per 0.1% below target shall apply automatically. Upon termination, "
            "the Contractor shall provide data export in standard format and maintain read-only access "
            "for ninety (90) days. Twelve (12) months' notice required before end-of-life."
        ),
        "source": "GC Cloud Framework / Custom",
        "notes": "Ensure data residency in Canada. Require GC Cloud Guardrails compliance assessment.",
    },
    {
        "id": "AGILE-001",
        "category": "Agile Development",
        "title": "Agile Sprint-Based Delivery",
        "tags": ["agile", "sprint", "scrum", "product backlog", "iteration", "DevOps"],
        "text": (
            "The Work shall be delivered using Agile methodology with two-week sprint cycles. Each sprint "
            "shall produce potentially shippable increments per the prioritized product backlog. Sprint "
            "planning, reviews, and retrospectives shall include Canada's Product Owner. Acceptance of "
            "each sprint deliverable shall be confirmed within five (5) business days."
        ),
        "source": "GC Digital Standards / Custom",
        "notes": "Align with GC Digital Standards. Define 'Definition of Done' in Schedule A.",
    },
]


# ── Search ─────────────────────────────────────────────────────────────────────

def search_clauses(query: str, category: Optional[str] = None) -> list[dict]:
    """
    Search the clause library by keyword(s) and optional category filter.
    Returns matching clauses ranked by relevance (simple term frequency).
    """
    query_lower = query.lower()
    query_terms = re.split(r"\W+", query_lower)

    results = []
    for clause in CLAUSE_DB:
        # Category filter
        if category and clause["category"].lower() != category.lower():
            continue

        # Score: count matches across title, tags, text, category
        score = 0
        search_target = " ".join([
            clause["title"].lower(),
            " ".join(clause["tags"]),
            clause["text"].lower(),
            clause["category"].lower(),
        ])
        for term in query_terms:
            if len(term) > 2:  # skip short stop words
                score += search_target.count(term)

        if score > 0:
            results.append({**clause, "_score": score})

    # Sort by score descending
    return sorted(results, key=lambda c: c["_score"], reverse=True)


def get_clause(clause_id: str) -> Optional[dict]:
    """Retrieve a specific clause by its ID."""
    for clause in CLAUSE_DB:
        if clause["id"] == clause_id:
            return clause
    return None


def list_categories() -> list[str]:
    """Return all unique clause categories."""
    return sorted(set(c["category"] for c in CLAUSE_DB))


def list_clauses(category: Optional[str] = None) -> list[dict]:
    """List all clauses, optionally filtered by category."""
    if category:
        return [c for c in CLAUSE_DB if c["category"].lower() == category.lower()]
    return CLAUSE_DB
