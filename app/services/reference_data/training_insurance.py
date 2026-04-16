"""
Advanced training data — Part 6: Insurance requirements training.
Risk-to-coverage mapping, threshold logic, and endorsement requirements.
"""

# ── Risk Scenario → Insurance Requirement Pairs ──────────────

INSURANCE_RISK_MAPPING_TRAINING = [
    {
        "instruction": "Determine the insurance requirements for this scope of work. Return JSON with required policies, limits, endorsements, and rationale.",
        "input": "A consultant providing strategic financial advisory services to the Government of Canada. Contract value: $500,000. Duration: 12 months.",
        "output": '{"required_policies": [{"type": "Professional Liability (E&O)", "limit_per_claim": "$2,000,000", "aggregate": "$2,000,000", "rationale": "Financial advice creates risk of economic loss from negligent recommendations. E&O covers claims of professional negligence, errors, or omissions."}, {"type": "Commercial General Liability (CGL)", "limit_per_occurrence": "$2,000,000", "aggregate": "$2,000,000", "rationale": "Standard coverage for bodily injury and property damage. Required for all on-site work at government facilities."}], "endorsements": ["Canada named as Additional Insured on CGL", "Cross-Liability clause", "30-day notice of cancellation to Canada"], "proof_timeline": "Certificate of Insurance within 10 business days of contract award", "threshold_logic": "Contract value $500K → minimum $2M per policy per Treasury Board guidelines"}'
    },
    {
        "instruction": "Determine the insurance requirements for this scope of work. Return JSON with required policies, limits, endorsements, and rationale.",
        "input": "A construction contractor performing bridge rehabilitation on a federal highway. Contract value: $28,000,000. Duration: 18 months. Work involves excavation near a river.",
        "output": '{"required_policies": [{"type": "Commercial General Liability (CGL)", "limit_per_occurrence": "$10,000,000", "aggregate": "$10,000,000", "rationale": "High-value construction with public exposure. $10M required for contracts over $10M per PWGSC guidelines."}, {"type": "Environmental/Pollution Liability", "limit_per_occurrence": "$5,000,000", "aggregate": "$5,000,000", "rationale": "Excavation near water creates pollution risk. Covers sudden and gradual pollution events, remediation costs."}, {"type": "Automobile Liability", "limit_per_occurrence": "$5,000,000", "rationale": "Heavy equipment and vehicles on highway right-of-way."}, {"type": "Builders Risk (Course of Construction)", "limit": "Full replacement value of the project", "rationale": "Covers damage to the work during construction from fire, weather, vandalism, etc."}, {"type": "Workers Compensation", "limit": "Statutory", "rationale": "Mandatory under provincial workers compensation legislation for all construction workers."}], "endorsements": ["Canada named as Additional Insured on CGL and Auto", "Cross-Liability clause on CGL", "Waiver of Subrogation in favour of Canada on Builders Risk", "30-day notice of cancellation to Canada", "Blanket Contractual Liability on CGL"], "proof_timeline": "Certificate of Insurance within 14 calendar days of contract award, before mobilization", "threshold_logic": "Contract value $28M → $10M CGL (contracts >$10M). Pollution liability required due to work near water. Builders Risk at full replacement value per SACC Section 5."}'
    },
    {
        "instruction": "Determine the insurance requirements for this scope of work. Return JSON with required policies, limits, endorsements, and rationale.",
        "input": "A SaaS vendor hosting Protected B government data in Canadian data centres. Contract value: $3,600,000/year. The vendor processes personal information of 500,000+ citizens.",
        "output": '{"required_policies": [{"type": "Cyber Liability / Network Security", "limit_per_claim": "$5,000,000", "aggregate": "$5,000,000", "rationale": "Protected B data + 500K personal records = high breach exposure. Covers data breach response, notification costs, credit monitoring, regulatory fines, and network security liability."}, {"type": "Technology Errors & Omissions", "limit_per_claim": "$5,000,000", "aggregate": "$5,000,000", "rationale": "SaaS platform failures could disrupt government operations. Covers claims of technology failure, service interruption, and software defects."}, {"type": "Commercial General Liability (CGL)", "limit_per_occurrence": "$5,000,000", "aggregate": "$5,000,000", "rationale": "Standard third-party liability coverage."}], "endorsements": ["Canada named as Additional Insured on CGL", "Cyber policy must include first-party AND third-party coverage", "No exclusion for regulatory fines where insurable by law", "Retroactive date no later than contract commencement", "30-day notice of cancellation to Canada"], "proof_timeline": "Certificate of Insurance within 10 business days of contract award", "threshold_logic": "Annual value $3.6M + Protected B data + 500K records → $5M cyber and tech E&O. High data sensitivity justifies limits above standard $2M threshold."}'
    },
    {
        "instruction": "Determine the insurance requirements for this scope of work. Return JSON with required policies, limits, endorsements, and rationale.",
        "input": "A janitorial services company providing cleaning services at a federal office building. Contract value: $85,000/year. 5 cleaning staff on-site daily.",
        "output": '{"required_policies": [{"type": "Commercial General Liability (CGL)", "limit_per_occurrence": "$2,000,000", "aggregate": "$2,000,000", "rationale": "On-site workers create slip/fall and property damage risk. Standard minimum for service contracts."}, {"type": "Workers Compensation", "limit": "Statutory", "rationale": "Mandatory for all employees. Contractor must provide WSIB clearance certificate."}, {"type": "Fidelity Bond / Employee Dishonesty", "limit": "$100,000", "rationale": "Staff have unsupervised access to federal premises after hours. Covers theft by employees."}], "endorsements": ["Canada named as Additional Insured on CGL", "Cross-Liability clause", "30-day notice of cancellation"], "proof_timeline": "Certificate of Insurance within 10 business days of award", "threshold_logic": "Contract value <$100K → $2M CGL minimum. Fidelity bond required due to unsupervised premises access."}'
    },
    {
        "instruction": "Determine the insurance requirements for this scope of work. Return JSON with required policies, limits, endorsements, and rationale.",
        "input": "An architecture firm designing a new federal laboratory. Contract value: $2,100,000. The lab will handle hazardous biological materials (BSL-3).",
        "output": '{"required_policies": [{"type": "Professional Liability (E&O)", "limit_per_claim": "$5,000,000", "aggregate": "$5,000,000", "rationale": "Design errors for a BSL-3 lab could result in catastrophic containment failure. Higher-than-standard E&O limits required due to hazardous use."}, {"type": "Commercial General Liability (CGL)", "limit_per_occurrence": "$5,000,000", "aggregate": "$5,000,000", "rationale": "On-site inspections and potential design liability."}, {"type": "Pollution Liability", "limit_per_occurrence": "$5,000,000", "rationale": "BSL-3 facility design must account for biological containment. Design failure could lead to environmental contamination claims."}], "endorsements": ["Canada named as Additional Insured on CGL", "E&O policy must not exclude biological/chemical hazard design", "Extended reporting period (tail coverage) of 5 years post-completion", "30-day notice of cancellation"], "proof_timeline": "Certificate of Insurance within 10 business days of award", "threshold_logic": "Contract value $2.1M + BSL-3 hazardous facility → $5M E&O and pollution (elevated from standard $2M due to catastrophic risk potential). Tail coverage essential — design defects may not manifest for years."}'
    },
    {
        "instruction": "Determine the insurance requirements for this scope of work. Return JSON with required policies, limits, endorsements, and rationale.",
        "input": "A medical equipment supplier providing MRI machines to 8 hospital sites. Contract value: $25,000,000. Includes installation, training, and 7-year maintenance.",
        "output": '{"required_policies": [{"type": "Commercial General Liability (CGL)", "limit_per_occurrence": "$10,000,000", "aggregate": "$10,000,000", "rationale": "Medical equipment creates patient safety risk. $10M required for contracts over $10M."}, {"type": "Product Liability", "limit_per_occurrence": "$10,000,000", "aggregate": "$10,000,000", "rationale": "MRI equipment malfunction could cause patient injury. Product liability covers claims arising from defective goods."}, {"type": "Professional Liability (E&O)", "limit_per_claim": "$5,000,000", "rationale": "Installation and calibration errors could affect diagnostic accuracy."}, {"type": "Workers Compensation", "limit": "Statutory", "rationale": "Installation technicians on hospital sites."}], "endorsements": ["Canada/Hospital named as Additional Insured on CGL and Product Liability", "Product recall coverage", "Cross-Liability clause", "No MRI/radiation exclusion on CGL", "30-day notice of cancellation"], "proof_timeline": "Certificate of Insurance within 14 days of award", "threshold_logic": "Contract value $25M + medical equipment + patient safety → $10M CGL and product liability. Product recall endorsement critical for medical devices. Coverage must extend through 7-year maintenance period."}'
    },
]

# ── Insurance Threshold Lookup Table Training ────────────────

INSURANCE_THRESHOLD_TRAINING = [
    {
        "instruction": "What are the standard Canadian federal procurement insurance thresholds? Provide the lookup table mapping contract value to required insurance limits.",
        "input": "",
        "output": '{"threshold_table": [{"contract_value": "Under $100,000", "cgl": "$1,000,000 per occurrence", "eo": "$1,000,000 if professional services", "cyber": "Not typically required", "notes": "Minimum coverage for low-value contracts"}, {"contract_value": "$100,000 - $500,000", "cgl": "$2,000,000 per occurrence", "eo": "$2,000,000 if professional services", "cyber": "$1,000,000 if handling data", "notes": "Standard threshold per Treasury Board Guide"}, {"contract_value": "$500,000 - $2,000,000", "cgl": "$2,000,000 - $5,000,000", "eo": "$2,000,000 - $5,000,000", "cyber": "$2,000,000 if handling sensitive data", "notes": "Limits scaled based on risk profile"}, {"contract_value": "$2,000,000 - $10,000,000", "cgl": "$5,000,000", "eo": "$5,000,000", "cyber": "$2,000,000 - $5,000,000", "notes": "Mid-range contracts — assess specific risks"}, {"contract_value": "Over $10,000,000", "cgl": "$10,000,000+", "eo": "$5,000,000 - $10,000,000", "cyber": "$5,000,000+", "notes": "High-value — may require umbrella/excess policy"}], "special_requirements": {"construction": "Builders Risk at full replacement value + Labour & Material Bond", "it_cloud": "Cyber Liability mandatory for any data handling", "hazardous": "Pollution Liability required for environmental risk", "medical": "Product Liability required for medical devices", "aviation_marine": "Aviation/Marine Liability for specialized operations"}, "source": "Treasury Board of Canada Guide to Insurance, PWGSC SACC Section 5(R)"}'
    },
]

# ── Insurance Terminology Training ───────────────────────────

INSURANCE_TERMINOLOGY_TRAINING = [
    {
        "instruction": "Define these insurance terms in the context of Canadian government procurement. Return JSON with each term's definition and practical significance.",
        "input": "Additional Insured, Waiver of Subrogation, Cross-Liability, Certificate of Insurance, Occurrence vs Claims-Made",
        "output": '{"definitions": [{"term": "Additional Insured", "definition": "A party added to the Contractor\'s insurance policy who receives coverage under that policy. In procurement, Canada (the Crown) is named as Additional Insured on the Contractor\'s CGL policy.", "practical_significance": "If a third party sues Canada for something the Contractor caused, the Contractor\'s insurer must defend and indemnify Canada. Without this, Canada would need to claim against the Contractor directly."}, {"term": "Waiver of Subrogation", "definition": "The insurer waives its right to recover (subrogate) against the named party after paying a claim. In procurement, the Contractor\'s insurer waives subrogation rights against Canada.", "practical_significance": "Prevents the Contractor\'s insurer from suing Canada to recover claim payments. Common on Builders Risk policies where both parties have insurable interest."}, {"term": "Cross-Liability", "definition": "A clause treating each insured party as if they had a separate policy. One Additional Insured can claim against another under the same policy.", "practical_significance": "If Canada is injured by the Contractor\'s negligence, Canada can claim under the Contractor\'s CGL even though both are named insureds on the same policy."}, {"term": "Certificate of Insurance (COI)", "definition": "A document issued by the insurer confirming the types of coverage, limits, effective dates, and named insureds. It is evidence of insurance but does NOT confer coverage.", "practical_significance": "Canada requires COIs within 10 business days of contract award as proof of compliance. Always verify the COI matches the contract requirements — check limits, Additional Insured status, and policy dates."}, {"term": "Occurrence vs Claims-Made", "definition": "Occurrence: covers events that happen during the policy period regardless of when the claim is filed. Claims-Made: covers claims filed during the policy period regardless of when the event occurred. Claims-Made requires a retroactive date and extended reporting period (tail).", "practical_significance": "CGL is typically occurrence-based. Professional Liability (E&O) and Cyber are often claims-made. For claims-made policies, always require: (a) retroactive date no later than contract start; (b) tail coverage of 2+ years after contract end."}]}'
    },
]

# ── SACC Insurance Templates Training ────────────────────────

SACC_INSURANCE_TRAINING = [
    {
        "instruction": "What are the standard SACC (Standard Acquisition Clauses and Conditions) insurance requirements for a federal IT services contract? Provide the exact SACC reference and clause language.",
        "input": "IT managed services contract, $1.5M annual value, hosting Protected B data",
        "output": '{"sacc_reference": "SACC Manual Section 5 — Insurance Requirements (R-series)", "applicable_clauses": [{"clause": "R1250D — Commercial General Liability", "text": "The Contractor must obtain Commercial General Liability insurance with a limit of not less than $2,000,000 per occurrence and $2,000,000 in the annual aggregate, inclusive of defence costs. Canada must be named as Additional Insured. The policy must include Cross-Liability and Blanket Contractual Liability."}, {"clause": "R1260D — Professional Liability (E&O)", "text": "The Contractor must obtain Professional Liability (Errors and Omissions) insurance with a limit of not less than $2,000,000 per claim and in the aggregate. The policy must have a retroactive date no later than the commencement date of the Contract. If the policy is claims-made, the Contractor must maintain coverage for at least 2 years after contract completion."}, {"clause": "R1270D — Cyber Liability", "text": "The Contractor must obtain Cyber Liability insurance with a limit of not less than $2,000,000 per claim and in the aggregate, covering: network security liability, privacy liability, data breach response costs, regulatory defence costs, and media liability. The policy must cover both first-party and third-party losses."}], "additional_requirements": {"proof": "Certificate of Insurance within 10 business days of contract award", "cancellation_notice": "30 days written notice to the Contracting Authority", "currency": "All limits in Canadian dollars", "deductible": "Contractor responsible for all deductibles — deductibles must not exceed $50,000 without approval"}, "risk_note": "For Protected B data at $1.5M/year, consider increasing cyber limits to $5M. Standard $2M may be insufficient given data sensitivity and 500K+ potential affected individuals."}'
    },
]

# ── Combined export ──────────────────────────────────────────

# ── Chain-of-Thought Insurance Reasoning ─────────────────────

INSURANCE_COT_TRAINING = [
    {
        "instruction": "Determine insurance requirements for a cloud-based payroll system procurement.",
        "input": "Contract Value: $500k. Data Type: PII and Financial. Risk: High impact if data is breached.",
        "output": '{"reasoning": "The primary risk is digital data loss and financial error, not physical injury. The system processes PII (names, SINs, addresses) and financial data (salaries, bank accounts) for potentially thousands of employees. A breach could trigger mandatory PIPEDA notification, class action litigation, and regulatory fines. Therefore, Cyber Liability is prioritized over high CGL.", "requirements": [{"type": "Cyber Liability", "limit": "$5,000,000", "rationale": "PII volume and financial data sensitivity demand high cyber limits"}, {"type": "Professional Liability (E&O)", "limit": "$2,000,000", "rationale": "Payroll calculation errors could cause direct financial loss"}, {"type": "Commercial General Liability (CGL)", "limit": "$1,000,000", "rationale": "Minimal physical risk — standard minimum sufficient"}], "priority_order": "Cyber > E&O > CGL"}'
    },
    {
        "instruction": "Determine insurance requirements for a janitorial services tender.",
        "input": "Contract Value: $50k. Environment: Public Government Office. Risk: Slip and fall; property damage.",
        "output": '{"reasoning": "Risk is primarily physical and occupational. No sensitive data handling or professional advice involved. Cleaning staff have after-hours unsupervised access to government offices containing documents and equipment, creating theft/dishonesty risk. Workers are exposed to chemical cleaning agents and physical hazards (wet floors, ladders).", "requirements": [{"type": "Commercial General Liability (CGL)", "limit": "$2,000,000 per occurrence", "rationale": "Slip-and-fall and property damage are primary third-party risks"}, {"type": "Workers Compensation", "limit": "Statutory", "rationale": "Mandatory for all employees — chemical exposure and physical hazards"}, {"type": "Fidelity Bond", "limit": "$50,000", "rationale": "Unsupervised access to government offices requires employee dishonesty coverage"}], "priority_order": "CGL > Workers Comp > Fidelity"}'
    },
    {
        "instruction": "Determine insurance requirements for a structural engineering bridge inspection.",
        "input": "Contract Value: $1.2M. Risk: Catastrophic structural failure from missed defect; professional negligence.",
        "output": '{"reasoning": "High professional indemnity risk. If the engineer misses a critical structural defect during inspection, the bridge could fail, causing deaths and massive liability. The professional opinion IS the deliverable — E&O is the critical anchor policy. Physical presence on bridge sites also requires standard CGL and auto coverage for site vehicles.", "requirements": [{"type": "Professional Liability (E&O)", "limit": "$5,000,000", "rationale": "Catastrophic failure risk from missed defect — this is the primary risk vector"}, {"type": "Commercial General Liability (CGL)", "limit": "$5,000,000", "rationale": "On-site work on active highway infrastructure with public exposure"}, {"type": "Automobile Liability", "limit": "$2,000,000", "rationale": "Inspection vehicles operating on highway right-of-way"}], "priority_order": "E&O > CGL > Auto"}'
    },
    {
        "instruction": "Determine insurance requirements for a military base security guard services contract.",
        "input": "Contract Value: $3.5M/year. Environment: DND facility with restricted areas. Guards are armed. Personnel require Secret clearance.",
        "output": '{"reasoning": "Armed security at a military facility creates elevated bodily injury and wrongful act risk. Guards carry firearms and have authority to detain — this requires specific coverage for assault, battery, and wrongful detention. The military environment means potential exposure to classified information and restricted materials.", "requirements": [{"type": "Commercial General Liability (CGL)", "limit": "$10,000,000 per occurrence", "rationale": "Armed personnel with detention authority — high bodily injury risk"}, {"type": "Employers Liability", "limit": "$5,000,000", "rationale": "Guards exposed to on-duty injury risk beyond standard Workers Comp"}, {"type": "Errors & Omissions / Security Guard Liability", "limit": "$5,000,000", "rationale": "Covers wrongful detention, false arrest, assault, failure to protect"}, {"type": "Workers Compensation", "limit": "Statutory", "rationale": "Mandatory — elevated risk environment"}, {"type": "Fidelity Bond", "limit": "$500,000", "rationale": "Access to restricted military areas and classified materials"}], "priority_order": "CGL > Security Guard E&O > Fidelity > Workers Comp"}'
    },
]

# ── Insurance Red Flags Training ─────────────────────────────

INSURANCE_RED_FLAGS_TRAINING = [
    {
        "instruction": "Review this Certificate of Insurance for red flags. Identify all issues that could leave the Purchaser unprotected. Return JSON with each red flag, severity, and recommended action.",
        "input": "Certificate of Insurance for IT Services Contract ($2M/year). Policies: CGL $2M aggregate (claims-made), E&O $1M per claim with $100,000 deductible, no Cyber Liability. Additional Insured: Not listed. Waiver of Subrogation: Not included. Insurer: Acme Insurance Co (AM Best: B+ VI). Policy Period: Jan 1 2024 - Jan 1 2025. Contract Period: Apr 1 2025 - Mar 31 2028. Notice of Cancellation: 10 days.",
        "output": '{"red_flags": [{"flag": "CGL is Claims-Made instead of Occurrence", "severity": "High", "issue": "CGL should be occurrence-based. Claims-made CGL means if the policy lapses, past incidents are not covered. This is non-standard and restrictive.", "action": "Require occurrence-based CGL or mandate 3-year extended reporting period (tail)"}, {"flag": "CGL limit is Aggregate only, not Per Occurrence", "severity": "High", "issue": "A $2M aggregate limit shared across all clients means the limit could be exhausted by other claims before the Purchaser needs it. Per occurrence is the gold standard.", "action": "Require $2M PER OCCURRENCE and $2M aggregate at minimum"}, {"flag": "Missing Additional Insured endorsement", "severity": "Critical", "issue": "The Purchaser is not named as Additional Insured on the CGL. Without this, the Purchaser has no direct right to claim under the vendor\'s policy.", "action": "Reject COI — require Additional Insured endorsement naming the Purchaser"}, {"flag": "No Cyber Liability coverage", "severity": "Critical", "issue": "IT services contract handling data with NO cyber coverage. Any data breach, ransomware, or network security incident is completely uninsured.", "action": "Require Cyber Liability minimum $2M for this contract value"}, {"flag": "E&O deductible of $100,000 is excessive", "severity": "Medium", "issue": "If the vendor cannot pay the $100K deductible out-of-pocket, insurance effectively does not respond for smaller claims.", "action": "Require maximum deductible of $25,000-$50,000 or evidence of vendor\'s ability to self-insure the deductible"}, {"flag": "Policy expired before contract start", "severity": "Critical", "issue": "Policy ends Jan 1 2025 but contract starts Apr 1 2025. There is a 3-month gap with NO coverage.", "action": "Require current policy covering the full contract period. COI must show policy dates that encompass Apr 1 2025 - Mar 31 2028"}, {"flag": "No Waiver of Subrogation", "severity": "Medium", "issue": "Without waiver, the vendor\'s insurer could sue the Purchaser to recover claim payments.", "action": "Require Waiver of Subrogation in favour of the Purchaser"}, {"flag": "Insurer AM Best rating B+ VI is below minimum", "severity": "High", "issue": "A- VII is the standard minimum financial strength rating. B+ VI indicates the insurer may not have sufficient financial resources to pay large claims.", "action": "Require insurer rated A- VII or better by AM Best"}, {"flag": "Notice of Cancellation only 10 days", "severity": "Medium", "issue": "10 days is insufficient to find replacement coverage. Industry standard is 30 days.", "action": "Require 30-day prior written notice of cancellation to the Purchaser"}, {"flag": "E&O limit of $1M is below threshold", "severity": "Medium", "issue": "For a $2M/year IT contract, E&O should be at least $2M per Treasury Board guidelines.", "action": "Require E&O minimum $2M per claim and aggregate"}], "summary": {"total_flags": 10, "critical": 3, "high": 3, "medium": 4}, "verdict": "REJECT — COI has 3 critical deficiencies (no Additional Insured, no Cyber, expired policy). Do not proceed until all critical and high issues are resolved."}'
    },
    {
        "instruction": "List the top 10 insurance red flags an sLM should detect when reviewing vendor insurance submissions for Canadian government procurement.",
        "input": "",
        "output": '{"red_flags": [{"rank": 1, "flag": "Aggregate-Only Limits (no Per Occurrence)", "why": "A $2M aggregate shared across all the vendor\'s clients could be exhausted before the Purchaser needs it. Always require per-occurrence limits.", "check": "Verify COI shows both per-occurrence AND aggregate limits"}, {"rank": 2, "flag": "Missing Additional Insured Endorsement", "why": "Without it, the Purchaser has no direct coverage under the vendor\'s policy. The Purchaser would have to sue the vendor, then the vendor claims on insurance — adding months of delay.", "check": "COI must explicitly name the Purchaser as Additional Insured on CGL"}, {"rank": 3, "flag": "Lapsed or Expired Policy Dates", "why": "A COI with an expiry date before the contract start date means zero coverage from day one.", "check": "Policy period must encompass the entire contract term including renewals"}, {"rank": 4, "flag": "Excessive Deductibles", "why": "A $100K+ deductible means the vendor pays out-of-pocket before insurance responds. If the vendor cannot afford the deductible, claims go unpaid.", "check": "Deductibles should not exceed $25K-$50K without evidence of vendor financial capacity"}, {"rank": 5, "flag": "Geographic Exclusions", "why": "Policy excludes the province or territory where work is performed. Common with US-based vendors whose policies exclude Canadian operations.", "check": "Verify policy territory includes all project locations"}, {"rank": 6, "flag": "Claims-Made CGL (should be Occurrence)", "why": "Claims-made CGL only covers claims filed during the policy period. If the policy lapses, past incidents become uninsured. Occurrence-based covers incidents that happen during the policy period regardless of when the claim is filed.", "check": "CGL must be occurrence-based. If claims-made, require 3+ year tail"}, {"rank": 7, "flag": "Cyber Exclusion in E&O Policy", "why": "A tech vendor whose E&O policy specifically excludes data breaches, cyber attacks, or network security incidents. This is the #1 risk for IT contracts.", "check": "For IT contracts, verify E&O does not exclude cyber events — or require separate Cyber Liability policy"}, {"rank": 8, "flag": "Insurer Below A- VII AM Best Rating", "why": "A financially weak insurer may not be able to pay claims. The vendor has insurance on paper but cannot collect when needed.", "check": "Require minimum AM Best rating of A- VII (Excellent with strong financial size)"}, {"rank": 9, "flag": "No Waiver of Subrogation", "why": "After paying a claim, the insurer could sue the Purchaser to recover the money. This defeats the purpose of requiring the vendor to carry insurance.", "check": "Require Waiver of Subrogation in favour of the Purchaser on all policies"}, {"rank": 10, "flag": "Insufficient Notice of Cancellation", "why": "If the vendor\'s policy is cancelled with only 10 days notice, the Purchaser has no time to react. Standard is 30 days prior written notice.", "check": "Require 30-day written notice of cancellation, non-renewal, or material change"}]}'
    },
]

# ── PDF Extraction Tool (for Kaggle/VPS use) ─────────────────

INSURANCE_EXTRACTION_CODE = '''
"""
Insurance clause extractor — scans PDFs for insurance-related content.
Use on Kaggle or VPS to build training data from real procurement documents.

Usage:
    from app.services.reference_data.training_insurance import extract_insurance_clauses
    clauses = extract_insurance_clauses("./tender_documents")
"""
import os
import json

def extract_insurance_clauses(folder_path: str, output_file: str = "insurance_clauses.jsonl") -> list:
    """Extract insurance-related paragraphs from PDFs in a folder."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("Install PyMuPDF: pip install PyMuPDF")
        return []

    keywords = [
        "insurance", "liability", "indemnification", "policy", "coverage",
        "additional insured", "waiver of subrogation", "certificate of insurance",
        "deductible", "aggregate", "per occurrence", "workers compensation",
        "errors and omissions", "professional liability", "cyber liability",
        "fidelity bond", "builders risk", "pollution liability",
    ]

    extracted = []
    for file in os.listdir(folder_path):
        if not file.lower().endswith(".pdf"):
            continue
        try:
            doc = fitz.open(os.path.join(folder_path, file))
            full_text = "".join(page.get_text() for page in doc)
            paragraphs = full_text.split("\\n\\n")
            for para in paragraphs:
                para_lower = para.lower().strip()
                if len(para_lower) < 30:
                    continue
                if any(kw in para_lower for kw in keywords):
                    extracted.append({"source": file, "clause": para.strip()})
        except Exception as e:
            print(f"Error processing {file}: {e}")

    if output_file:
        with open(output_file, "w") as f:
            for entry in extracted:
                f.write(json.dumps(entry) + "\\n")
        print(f"Extracted {len(extracted)} insurance clauses to {output_file}")

    return extracted
'''

ALL_INSURANCE_TRAINING = (
    INSURANCE_RISK_MAPPING_TRAINING
    + INSURANCE_THRESHOLD_TRAINING
    + INSURANCE_TERMINOLOGY_TRAINING
    + SACC_INSURANCE_TRAINING
    + INSURANCE_COT_TRAINING
    + INSURANCE_RED_FLAGS_TRAINING
)
