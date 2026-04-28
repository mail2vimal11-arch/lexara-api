# Canadian Procurement Knowledge Article Seed Data
#
# Each article is an atomic unit of guidance — a clause, mandatory
# requirement, evaluation criterion, KPI, or risk note — keyed by:
#   - jurisdiction_code   (None = applies to all jurisdictions)
#   - commodity_category_code   (None = applies to all commodities)
#   - section_type        (maps to SOWTemplate.sections.section_type)
#
# Sources cite the public legal/policy instrument the language is
# derived from. Where a specific clause number applies it is given in
# `source_ref`. URLs link to the originating regulator's site.
#
# Article IDs follow:
#   {SCOPE}-{COMMODITY}-{TYPE}-{SLUG}-{NN}
# e.g. FED-IT_CLOUD-CLAUSE-DATA-RESIDENCY-001
#
# When importance == "critical" or is_mandatory == True, the workbench
# pins the article to the top of the right-pane intelligence list.

KNOWLEDGE_ARTICLES = [
    # =================================================================
    # FEDERAL — IT CLOUD: data residency
    # =================================================================
    {
        "article_id": "FED-IT_CLOUD-CLAUSE-DATA-RESIDENCY-001",
        "jurisdiction_code": "FED",
        "commodity_category_code": "IT_CLOUD",
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "sow_drafting",
        "section_type": "mandatory_requirements",
        "title": "Canadian Data Residency for Federal Cloud Services",
        "title_fr": "Résidence des données au Canada — services infonuagiques fédéraux",
        "content": (
            "Federal Protected B and below information must be stored, processed and "
            "supported from data centres located within Canada when using cloud services, "
            "per the Treasury Board Direction on the Secure Use of Commercial Cloud Services "
            "and CCCS Cloud Service Provider Information Technology Security Assessment "
            "Process. Backup, replication and recovery copies are likewise required to "
            "remain in Canada. The supplier must disclose all locations where Canadian data "
            "is stored, accessed, or processed, including any sub-processor arrangements."
        ),
        "template_text": (
            "1. Data Residency. The Contractor shall store, process, replicate, back up "
            "and provide support for all Government of Canada data classified Protected B "
            "or lower exclusively from data centres physically located within Canada. "
            "The Contractor shall not, without the prior written consent of the Contracting "
            "Authority, transfer, copy, or expose any such data outside Canada, including "
            "for the purposes of administration, support, monitoring, or analytics.\n\n"
            "2. Disclosure. The Contractor shall, upon execution of this Contract and "
            "annually thereafter, provide a written attestation listing all data centres, "
            "support centres, and sub-processors that store, access, or process Government "
            "of Canada data, together with the address of each such facility.\n\n"
            "3. Foreign Access. The Contractor shall promptly notify the Contracting "
            "Authority of any foreign legal demand (e.g., production orders, subpoenas, "
            "or analogous instruments) requesting access to Government of Canada data, "
            "to the extent such notification is permitted by applicable law."
        ),
        "guidance_note": (
            "Validate the supplier's CCCS assessment status (Protected B Medium Integrity "
            "Medium Availability) before contract award. PSPC's standard cloud services "
            "supply arrangement (EN578-200067/E) already incorporates this language; if "
            "drafting outside the SA, reproduce the residency requirement verbatim. The "
            "Contracting Authority should also reference the Policy on Service and Digital."
        ),
        "source": "TB_POLICY",
        "source_ref": "Direction on the Secure Use of Commercial Cloud Services (2017); GC ITSG-33",
        "source_url": "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/cloud-services.html",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["cloud", "data residency", "Protected B", "PIPEDA", "CCCS"],
        "related_article_ids": ["FED-ANY-CLAUSE-PRIVACY-PIPEDA-002", "FED-ANY-CLAUSE-SECURITY-CLEARANCE-005"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — Privacy / PIPEDA / Privacy Act
    # =================================================================
    {
        "article_id": "FED-ANY-CLAUSE-PRIVACY-PIPEDA-002",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "sow_drafting",
        "section_type": "terms_conditions",
        "title": "Privacy Act / PIPEDA Compliance",
        "title_fr": "Conformité à la Loi sur la protection des renseignements personnels",
        "content": (
            "Where personal information is handled on behalf of a federal institution, "
            "the contractor is bound by the Privacy Act and the institution's PIA. "
            "Where personal information is collected from individuals in the course of "
            "commercial activity, PIPEDA also applies. SOWs must oblige the contractor "
            "to implement reasonable safeguards and breach-notification procedures."
        ),
        "template_text": (
            "Privacy and Personal Information.\n"
            "(a) The Contractor shall handle all Personal Information collected, used, "
            "disclosed, retained or destroyed under this Contract in accordance with the "
            "Privacy Act (R.S.C. 1985, c. P-21), and where applicable, the Personal "
            "Information Protection and Electronic Documents Act (S.C. 2000, c. 5).\n"
            "(b) The Contractor shall implement administrative, technical, and physical "
            "safeguards appropriate to the sensitivity of the Personal Information, "
            "consistent with TBS' Directive on Privacy Practices.\n"
            "(c) The Contractor shall notify the Contracting Authority within 24 hours "
            "of becoming aware of any actual or suspected privacy breach involving "
            "Personal Information, and shall co-operate fully with any subsequent "
            "investigation or notification process.\n"
            "(d) Personal Information shall be returned or destroyed at the end of the "
            "Contract per the Contracting Authority's written direction."
        ),
        "guidance_note": (
            "If a PIA is required, attach it as an annex; if not, document the rationale "
            "in the procurement file. The TBS Directive on Privacy Impact Assessment is "
            "the controlling instrument."
        ),
        "source": "FEDERAL_LEGISLATION",
        "source_ref": "Privacy Act (R.S.C. 1985, c. P-21); PIPEDA (S.C. 2000, c. 5)",
        "source_url": "https://laws-lois.justice.gc.ca/eng/acts/p-21/",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["privacy", "PIPEDA", "Privacy Act", "breach notification"],
        "related_article_ids": ["FED-IT_CLOUD-CLAUSE-DATA-RESIDENCY-001"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — Limitation of Liability
    # =================================================================
    {
        "article_id": "FED-ANY-CLAUSE-LIMIT-LIABILITY-003",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "sow_drafting",
        "section_type": "terms_conditions",
        "title": "Limitation of Contractor Liability — Federal",
        "title_fr": "Limitation de la responsabilité du fournisseur — fédéral",
        "content": (
            "PSPC's Standard Acquisition Clauses and Conditions (SACC) provide a tiered "
            "limitation-of-liability regime that aligns the cap to contract value. The "
            "supplier's aggregate liability is generally capped at the greater of $2M "
            "or two times the contract value, with carve-outs for IP indemnity, third-"
            "party bodily injury / property damage, and breach of confidentiality."
        ),
        "template_text": (
            "Limitation of Liability.\n"
            "(a) Subject to paragraph (b), the Contractor's aggregate liability to Canada "
            "for any matter relating to or arising out of this Contract shall not exceed "
            "the greater of (i) two (2) times the total Contract Price; or (ii) "
            "$2,000,000 CAD.\n"
            "(b) The limit in paragraph (a) does not apply to: (i) damages for bodily "
            "injury (including death) or damage to real or tangible personal property "
            "caused by the Contractor's negligence; (ii) the Contractor's indemnification "
            "obligations under the Intellectual Property Infringement clause; (iii) the "
            "Contractor's confidentiality obligations; or (iv) damages arising from the "
            "Contractor's wilful misconduct or fraud.\n"
            "(c) Neither party shall be liable to the other for any indirect, incidental, "
            "consequential, exemplary, or punitive damages, including loss of profits or "
            "loss of data, except in respect of the carve-outs in paragraph (b)."
        ),
        "guidance_note": (
            "PSPC SACC manual clauses 2030 / 2035 are the canonical limitation-of-"
            "liability templates. Negotiating a lower cap is generally not authorised "
            "for federal SOWs without delegated authority."
        ),
        "source": "SACC",
        "source_ref": "PSPC SACC Manual, General Conditions clauses 2030 / 2035 (Limitation of Liability)",
        "source_url": "https://buyandsell.gc.ca/policy-and-guidelines/standard-acquisition-clauses-and-conditions-manual",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "high",
        "applies_above_value_cad": 25000.0,
        "applies_to_methods": ["RFP", "RFSO", "ITT"],
        "tags": ["liability", "indemnity", "SACC", "risk allocation"],
        "related_article_ids": ["FED-ANY-CLAUSE-IP-OWNERSHIP-004"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — IP Ownership (Crown ownership default)
    # =================================================================
    {
        "article_id": "FED-ANY-CLAUSE-IP-OWNERSHIP-004",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "sow_drafting",
        "section_type": "terms_conditions",
        "title": "Intellectual Property Ownership — Crown Default",
        "title_fr": "Propriété intellectuelle — propriété de la Couronne par défaut",
        "content": (
            "The Treasury Board Policy on Title to Intellectual Property establishes "
            "Crown ownership of foreground IP as the default, with limited exceptions "
            "where contractor ownership produces a better commercial outcome (e.g., "
            "where the contractor is in a position to exploit the IP). The default IP "
            "regime should be selected at the SOW drafting stage and recorded in the file."
        ),
        "template_text": (
            "Intellectual Property in Foreground Information.\n"
            "(a) Subject to paragraph (b), all rights — including copyright and any "
            "patentable subject matter — in any Foreground Information first conceived, "
            "developed or produced by the Contractor in the performance of this Contract "
            "shall vest in Canada as of the date of creation.\n"
            "(b) The parties agree that the Contractor retains a non-exclusive, royalty-"
            "free, perpetual licence to use Foreground Information solely for purposes "
            "incidental to performance of this Contract.\n"
            "(c) The Contractor shall execute, at Canada's request and expense, all "
            "documents required to perfect Canada's title to the Foreground Information, "
            "including assignments, declarations of inventorship, and waivers of moral "
            "rights, and shall obtain like documents from any sub-contractor or employee.\n"
            "(d) Background Information used by the Contractor remains the property of "
            "the original owner; the Contractor grants Canada an irrevocable, non-"
            "exclusive, worldwide, royalty-free licence to use such Background Information "
            "to the extent necessary to use the Foreground Information."
        ),
        "guidance_note": (
            "If contractor IP ownership is selected, document the rationale in the "
            "procurement file (e.g., \"Contractor will commercialise the work\"). "
            "Crown licence-back terms should still be secured in that case."
        ),
        "source": "TB_POLICY",
        "source_ref": "TB Policy on Title to Intellectual Property Arising under Crown Procurement Contracts",
        "source_url": "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=12541",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["IP", "intellectual property", "Crown ownership", "TBS policy"],
        "related_article_ids": ["FED-ANY-CLAUSE-LIMIT-LIABILITY-003"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — Security Clearance
    # =================================================================
    {
        "article_id": "FED-ANY-MANDATORY-SECURITY-CLEARANCE-005",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "mandatory_req",
        "procurement_phase": "solicitation",
        "section_type": "mandatory_requirements",
        "title": "Personnel Security Screening Requirements",
        "title_fr": "Exigences de filtrage de sécurité du personnel",
        "content": (
            "The Contract Security Program (CSP) administers personnel and organisation "
            "security screening for federal contractors. Where an SOW exposes contractor "
            "personnel to Protected or Classified information, the SOW must specify the "
            "level of clearance required (Reliability, Secret, Top Secret), and award is "
            "conditional on the contractor and named personnel holding the requisite "
            "clearance at contract start."
        ),
        "template_text": (
            "Mandatory Personnel Security. The Contractor and all of its personnel who "
            "will have access to {PROTECTED|SECRET|TOP_SECRET} information or assets in "
            "the performance of this Contract must, at contract award and throughout "
            "the term, hold a valid {RELIABILITY_STATUS|SECRET|TOP_SECRET} clearance "
            "issued by the PSPC Contract Security Program. The Contractor shall not "
            "assign personnel to perform under this Contract until they have been "
            "screened and authorised by the Contract Security Authority. Failure to "
            "maintain required clearances is a material breach of this Contract."
        ),
        "guidance_note": (
            "Confirm the security categorisation with the project's Departmental "
            "Security Officer. Build clearance lead-time into the schedule — Reliability "
            "is typically 2–4 weeks, Secret 6–9 months, Top Secret 12+ months. "
            "Consider permitting alternates where lead times are critical."
        ),
        "source": "TB_POLICY",
        "source_ref": "Policy on Government Security; Contract Security Manual",
        "source_url": "https://www.tpsgc-pwgsc.gc.ca/esc-src/index-eng.html",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "critical",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["security clearance", "Reliability", "Secret", "CSP"],
        "related_article_ids": ["FED-IT_CYBER-MANDATORY-CGP-006"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — Controlled Goods Program
    # =================================================================
    {
        "article_id": "FED-DEFENCE-MANDATORY-CGP-006",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "mandatory_req",
        "procurement_phase": "solicitation",
        "section_type": "mandatory_requirements",
        "title": "Controlled Goods Program Registration",
        "title_fr": "Inscription au Programme des marchandises contrôlées",
        "content": (
            "Where a federal contract involves examining, possessing, or transferring "
            "Controlled Goods (as defined in the Defence Production Act), the contractor "
            "and any sub-contractors must be registered with the Controlled Goods Program "
            "(CGP) administered by PSPC, and personnel must be CGP-assessed."
        ),
        "template_text": (
            "Controlled Goods. The Contractor and any sub-contractor that will examine, "
            "possess, or transfer Controlled Goods (as defined in the Defence Production "
            "Act, R.S.C. 1985, c. D-1) in the performance of this Contract must be "
            "registered with the Controlled Goods Program at the time of bid closing and "
            "must remain registered throughout the term. Personnel who handle Controlled "
            "Goods must have a current security assessment under the CGP."
        ),
        "guidance_note": (
            "Applies primarily to defence and aerospace work. Confirm the goods are "
            "scheduled in the Schedule to the Defence Production Act before invoking."
        ),
        "source": "FEDERAL_LEGISLATION",
        "source_ref": "Defence Production Act (R.S.C. 1985, c. D-1); Controlled Goods Regulations",
        "source_url": "https://www.tpsgc-pwgsc.gc.ca/pmc-cgp/index-eng.html",
        "is_mandatory": True,
        "importance": "high",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["controlled goods", "defence", "CGP"],
        "related_article_ids": ["FED-ANY-MANDATORY-SECURITY-CLEARANCE-005"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — Official Languages Act
    # =================================================================
    {
        "article_id": "FED-ANY-CLAUSE-OFFICIAL-LANGUAGES-007",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "sow_drafting",
        "section_type": "terms_conditions",
        "title": "Official Languages Act Compliance",
        "title_fr": "Conformité à la Loi sur les langues officielles",
        "content": (
            "Federal institutions must provide services and communications in both "
            "English and French. Contractors delivering services on the federal "
            "institution's behalf must do so in a manner that supports the institution's "
            "obligations under Part IV of the Official Languages Act."
        ),
        "template_text": (
            "Official Languages. Where the Contractor provides services to or "
            "communicates with the public on behalf of Canada, the Contractor shall do "
            "so in both official languages where Canada has a duty to communicate or "
            "provide services in both official languages under Part IV of the Official "
            "Languages Act (R.S.C. 1985, c. 31 (4th Supp.)). Documents, signage, "
            "instructions, and notifications produced for public-facing use shall be "
            "available in both English and French simultaneously and of equal quality."
        ),
        "guidance_note": (
            "Bilingual production capacity should be a mandatory requirement, not a "
            "rated criterion, for any public-facing federal deliverable."
        ),
        "source": "FEDERAL_LEGISLATION",
        "source_ref": "Official Languages Act (R.S.C. 1985, c. 31 (4th Supp.)), Part IV",
        "source_url": "https://laws-lois.justice.gc.ca/eng/acts/o-3.01/",
        "is_mandatory": True,
        "importance": "high",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["official languages", "bilingual", "OLA"],
        "related_article_ids": [],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — PSIB Indigenous procurement
    # =================================================================
    {
        "article_id": "FED-ANY-RATED-PSIB-INDIGENOUS-008",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "rated_req",
        "procurement_phase": "evaluation",
        "section_type": "rated_requirements",
        "title": "Procurement Strategy for Indigenous Business — Eligibility",
        "title_fr": "Stratégie d'approvisionnement auprès des entreprises autochtones",
        "content": (
            "The federal Procurement Strategy for Indigenous Business (PSIB) implements "
            "Canada's commitment that Indigenous businesses receive a minimum of 5% of "
            "federal contract value. PSIB-eligible suppliers must be on the Indigenous "
            "Business Directory and meet ownership/control criteria. Set-aside and "
            "voluntary procurements both invoke PSIB rules; sub-contracting to Indigenous "
            "businesses can also satisfy PSIB targets."
        ),
        "template_text": (
            "Indigenous Business Participation Plan (Rated). Bidders shall submit an "
            "Indigenous Business Participation Plan describing how Indigenous businesses, "
            "as defined under the Procurement Strategy for Indigenous Business, will be "
            "engaged in the performance of this Contract. The Plan shall identify the "
            "specific work packages, the percentage of contract value to be performed by "
            "or sub-contracted to Indigenous businesses, and the proposed reporting "
            "cadence. Plans will be evaluated on substance, evidence of supplier "
            "relationships, and credibility of the value commitment."
        ),
        "guidance_note": (
            "Confirm whether the procurement is set aside under PSIB or merely PSIB-"
            "applicable. Set-asides require all bidders be Indigenous-owned per the IBD."
        ),
        "source": "TB_POLICY",
        "source_ref": "Procurement Strategy for Indigenous Business (PSIB) — ISC Directive",
        "source_url": "https://www.sac-isc.gc.ca/eng/1100100032802/1610379932158",
        "is_mandatory": False,
        "importance": "high",
        "risk_if_omitted": "medium",
        "applies_above_value_cad": None,
        "applies_to_methods": ["RFP", "RFSO"],
        "tags": ["Indigenous", "PSIB", "set-aside"],
        "related_article_ids": [],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — CFTA Article 509 disclosure
    # =================================================================
    {
        "article_id": "FED-ANY-COMPLIANCE-CFTA-509-009",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "compliance_check",
        "procurement_phase": "solicitation",
        "section_type": "evaluation_methodology",
        "title": "CFTA Article 509 — Disclosure of Evaluation Criteria",
        "title_fr": "ALEC, article 509 — divulgation des critères d'évaluation",
        "content": (
            "Article 509 of the Canadian Free Trade Agreement requires that all "
            "evaluation criteria, the relative importance to be given to each, and any "
            "method to be applied to convert criteria scores into an award decision be "
            "disclosed to bidders in the solicitation. Failure to disclose is a frequent "
            "ground for bid challenges before the CITT or provincial review bodies."
        ),
        "template_text": (
            "Evaluation Methodology Disclosure. The evaluation criteria, point allocations, "
            "weighting between technical and financial scores, mandatory pass/fail "
            "thresholds, and the formula for combining technical and financial scores into "
            "an overall ranked score are fully disclosed in this solicitation document. "
            "No undisclosed criterion will influence the award decision. Any post-closing "
            "clarification will be limited to confirming statements already made in the "
            "bid and will not be used to enhance any bidder's score."
        ),
        "guidance_note": (
            "Run a pre-issuance checklist confirming weights, thresholds, and any "
            "tiebreaker rules are stated in plain language in the solicitation."
        ),
        "source": "CFTA",
        "source_ref": "Canadian Free Trade Agreement, Article 509 — Solicitation Documentation",
        "source_url": "https://www.cfta-alec.ca/wp-content/uploads/2017/06/CFTA-Consolidated-Text-Final-Print-Text-English.pdf",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "high",
        "applies_above_value_cad": 121200.0,
        "applies_to_methods": ["RFP", "ITT", "RFSO"],
        "tags": ["CFTA", "evaluation", "disclosure", "bid challenge"],
        "related_article_ids": ["FED-ANY-RISK-BID-CHALLENGE-010"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — Bid Challenge Risk Note
    # =================================================================
    {
        "article_id": "FED-ANY-RISK-BID-CHALLENGE-010",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "risk_note",
        "procurement_phase": "solicitation",
        "section_type": "evaluation_methodology",
        "title": "Bid Challenge Exposure — CITT and Trade Tribunals",
        "title_fr": "Risque de plainte — TCCE et autres tribunaux commerciaux",
        "content": (
            "Federal procurements that fall under CFTA, CUSMA, CETA, or WTO-GPA may be "
            "challenged before the Canadian International Trade Tribunal (CITT) within "
            "10 working days of when the basis of the complaint became known. The most "
            "common grounds are: undisclosed criteria, biased specifications, failure to "
            "follow the methodology described in the solicitation, and improper sole-source "
            "justification. A successful complaint can result in re-tendering, lost-profit "
            "remedies, or contract cancellation."
        ),
        "template_text": None,
        "guidance_note": (
            "Maintain contemporaneous evaluation records (consensus scoresheets, debrief "
            "notes, conflict-of-interest declarations) — these are essential evidence in "
            "any bid challenge."
        ),
        "source": "CITT_GUIDANCE",
        "source_ref": "Canadian International Trade Tribunal Procurement Inquiry Regulations",
        "source_url": "https://www.citt-tcce.gc.ca/en/procurement",
        "is_mandatory": False,
        "importance": "high",
        "risk_if_omitted": "high",
        "applies_above_value_cad": 121200.0,
        "applies_to_methods": ["RFP", "ITT", "RFSO"],
        "tags": ["CITT", "bid challenge", "trade agreement", "complaint"],
        "related_article_ids": ["FED-ANY-COMPLIANCE-CFTA-509-009"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — CUSMA / CETA implications
    # =================================================================
    {
        "article_id": "FED-ANY-COMPLIANCE-CUSMA-CETA-011",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "compliance_check",
        "procurement_phase": "sow_drafting",
        "section_type": "background",
        "title": "CUSMA / CETA Trade Agreement Coverage",
        "title_fr": "Couverture des accords ACEUM et AECG",
        "content": (
            "When the value of a federal procurement exceeds the CUSMA or CETA threshold "
            "for the relevant covered entity and commodity, the procurement must comply "
            "with the corresponding chapter on government procurement. Among other things, "
            "this requires non-discriminatory treatment of CUSMA / EU-origin suppliers, "
            "publication windows of at least 40 calendar days for full open competition, "
            "and disclosure of evaluation criteria and weights."
        ),
        "template_text": (
            "Trade Agreement Coverage. This procurement is subject to the government "
            "procurement chapter of {AGREEMENT_LIST}. The Contracting Authority will "
            "treat suppliers from each covered party on a non-discriminatory basis, "
            "post the solicitation for the minimum required period, and disclose all "
            "evaluation criteria and weights in this solicitation document."
        ),
        "guidance_note": (
            "Use the Treasury Board threshold tables (re-indexed every two years for CFTA, "
            "annually for CUSMA / CETA) to confirm coverage. Note that CUSMA and CETA "
            "thresholds in CAD are adjusted for currency."
        ),
        "source": "CUSMA",
        "source_ref": "CUSMA Chapter 13; CETA Chapter Nineteen",
        "source_url": "https://www.international.gc.ca/trade-commerce/trade-agreements-accords-commerciaux/agr-acc/cusma-aceum/index.aspx",
        "is_mandatory": True,
        "importance": "high",
        "risk_if_omitted": "high",
        "applies_above_value_cad": 99700.0,
        "applies_to_methods": ["RFP", "ITT", "RFSO"],
        "tags": ["CUSMA", "CETA", "trade agreement", "thresholds"],
        "related_article_ids": ["FED-ANY-COMPLIANCE-CFTA-509-009"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — Accessibility (ACA + WCAG 2.1 AA)
    # =================================================================
    {
        "article_id": "FED-IT_DIGITAL-CLAUSE-ACCESSIBILITY-012",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "sow_drafting",
        "section_type": "acceptance_criteria",
        "title": "Accessibility — Accessible Canada Act / WCAG 2.1 AA",
        "title_fr": "Accessibilité — Loi canadienne sur l'accessibilité / WCAG 2.1 AA",
        "content": (
            "Under the Accessible Canada Act and TBS' Standard on Web Accessibility, "
            "all digital products and services delivered to or for the federal government "
            "must conform to WCAG 2.1 Level AA. PDF and document deliverables follow "
            "PDF/UA-1. Acceptance criteria for digital deliverables must include passing "
            "an automated and manual accessibility audit."
        ),
        "template_text": (
            "Accessibility. All digital deliverables — including web applications, mobile "
            "applications, source documents, PDFs, and multimedia — shall conform to the "
            "Web Content Accessibility Guidelines (WCAG) 2.1 Level AA. PDF deliverables "
            "shall additionally conform to ISO 14289-1 (PDF/UA). At each acceptance "
            "milestone, the Contractor shall provide: (i) an Accessibility Conformance "
            "Report (ACR) using the most recent W3C template; (ii) automated audit results "
            "(e.g., Axe, WAVE) showing zero failures at AA; and (iii) manual audit results "
            "from a person with appropriate accessibility expertise."
        ),
        "guidance_note": (
            "Embed accessibility into rated requirements as well as acceptance criteria "
            "— remediation late in the project is expensive."
        ),
        "source": "FEDERAL_LEGISLATION",
        "source_ref": "Accessible Canada Act, S.C. 2019, c. 10; TBS Standard on Web Accessibility",
        "source_url": "https://laws-lois.justice.gc.ca/eng/acts/A-0.6/",
        "is_mandatory": True,
        "importance": "high",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["accessibility", "WCAG", "ACA", "PDF/UA"],
        "related_article_ids": [],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — AI / ADM Directive (TBS)
    # =================================================================
    {
        "article_id": "FED-IT_DATA_AI-COMPLIANCE-ADM-013",
        "jurisdiction_code": "FED",
        "commodity_category_code": "IT_DATA_AI",
        "commodity_subcategory_code": None,
        "article_type": "compliance_check",
        "procurement_phase": "sow_drafting",
        "section_type": "scope",
        "title": "Directive on Automated Decision-Making (ADM)",
        "title_fr": "Directive sur la prise de décisions automatisée",
        "content": (
            "Where AI is used to support an administrative decision affecting clients of "
            "a federal institution, TBS' Directive on Automated Decision-Making applies. "
            "Suppliers must support an Algorithmic Impact Assessment (AIA), implement "
            "transparency notices, peer reviews, and human-in-the-loop safeguards "
            "appropriate to the assessed impact level."
        ),
        "template_text": (
            "Algorithmic Decision-Making. Where any deliverable supports automated or "
            "AI-assisted administrative decisions affecting clients of {DEPARTMENT}, the "
            "Contractor shall: (i) co-operate in completing an Algorithmic Impact "
            "Assessment per the TBS Directive on Automated Decision-Making; (ii) provide "
            "model documentation, training-data lineage, and bias testing results "
            "appropriate to the assessed impact level; (iii) implement notice-to-client, "
            "explanation, and recourse mechanisms as defined in the AIA; and (iv) "
            "preserve audit logs for a minimum of seven (7) years."
        ),
        "guidance_note": (
            "Run the AIA tool early — its impact level (I–IV) drives the entire stack of "
            "obligations."
        ),
        "source": "TB_POLICY",
        "source_ref": "TBS Directive on Automated Decision-Making (latest revision)",
        "source_url": "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592",
        "is_mandatory": True,
        "importance": "high",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["AI", "ADM", "AIA", "responsible AI"],
        "related_article_ids": [],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # FEDERAL — Sole-source justification grounds (SACC)
    # =================================================================
    {
        "article_id": "FED-ANY-COMPLIANCE-SOLE-SOURCE-014",
        "jurisdiction_code": "FED",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "compliance_check",
        "procurement_phase": "sow_drafting",
        "section_type": "background",
        "title": "Sole-Source Justification — Government Contracts Regulations",
        "title_fr": "Justification du fournisseur unique — Règlement sur les marchés de l'État",
        "content": (
            "Section 6 of the Government Contracts Regulations (SOR/87-402) authorises "
            "non-competitive contracting only on four grounds: pressing emergency, "
            "contract under $25,000 (or $40,000 services in some categories), public "
            "interest where competition would not be served, and only one supplier "
            "capable. CFTA Article 513 mirrors this list with additional carve-outs. "
            "The justification must be documented in writing and signed by the "
            "contracting authority."
        ),
        "template_text": None,
        "guidance_note": (
            "A weak sole-source memo is the single most common cause of CITT findings "
            "against the Crown. Cite the specific regulatory paragraph and provide "
            "evidence (market scan, prior award history, technical incompatibility report)."
        ),
        "source": "FEDERAL_LEGISLATION",
        "source_ref": "Government Contracts Regulations, SOR/87-402, s. 6",
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-87-402/",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "critical",
        "applies_above_value_cad": None,
        "applies_to_methods": ["SOLE_SOURCE", "NPP"],
        "tags": ["sole source", "non-competitive", "GCR", "justification"],
        "related_article_ids": ["FED-ANY-RISK-BID-CHALLENGE-010"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # ONTARIO — BPS Procurement Directive
    # =================================================================
    {
        "article_id": "ON-ANY-CLAUSE-BPS-DIRECTIVE-015",
        "jurisdiction_code": "ON",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "regulatory_requirement",
        "procurement_phase": "sow_drafting",
        "section_type": "background",
        "title": "Ontario BPS Procurement Directive — Mandatory Requirements",
        "title_fr": "Directive sur les approvisionnements du SPL de l'Ontario",
        "content": (
            "The Broader Public Sector Procurement Directive applies to school boards, "
            "hospitals, universities, colleges, and provincial agencies. The Directive "
            "imposes mandatory requirements including: open and competitive procurement "
            "above prescribed thresholds, a five-supplier rotation rule for invitational "
            "competitions, mandatory posting on a public portal, conflict-of-interest "
            "declarations, and supplier debriefing rights."
        ),
        "template_text": (
            "BPS Compliance. This procurement has been conducted in accordance with the "
            "Ontario Broader Public Sector Procurement Directive. Open and competitive "
            "thresholds, posting requirements, evaluation methodology disclosure, and "
            "supplier debriefing rights have been met."
        ),
        "guidance_note": (
            "BPS thresholds: $100,000 (goods/services/construction) for open competition. "
            "Below that, an invitational competition with at least three suppliers is "
            "required for goods/services valued $100K–$199,999."
        ),
        "source": "ON_PROCUREMENT_ACT",
        "source_ref": "BPS Procurement Directive (Ontario MGCS, 2023)",
        "source_url": "https://www.ontario.ca/page/broader-public-sector-procurement-directive",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["Ontario", "BPS", "procurement directive"],
        "related_article_ids": ["ON-CON-CLAUSE-PROMPT-PAYMENT-016"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # ONTARIO — Construction Prompt Payment Act
    # =================================================================
    {
        "article_id": "ON-CON-CLAUSE-PROMPT-PAYMENT-016",
        "jurisdiction_code": "ON",
        "commodity_category_code": "CON_BUILDING",
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "sow_drafting",
        "section_type": "terms_conditions",
        "title": "Ontario Prompt Payment & Adjudication (Construction Act)",
        "title_fr": "Paiement rapide et arbitrage — Loi sur la construction (Ontario)",
        "content": (
            "Ontario's Construction Act (since 2018) imposes mandatory prompt-payment "
            "rules on construction contracts: an owner must pay a proper invoice within "
            "28 days, and a contractor must in turn pay sub-contractors within 7 days of "
            "receipt from the owner. Disputes are resolved by interim adjudication "
            "(decision in approximately 30 days), with parties retaining the right to "
            "litigate or arbitrate the merits afterward."
        ),
        "template_text": (
            "Prompt Payment and Adjudication.\n"
            "(a) The Owner shall pay each Proper Invoice from the Contractor within "
            "twenty-eight (28) days of receipt, in accordance with Part I.1 of the "
            "Construction Act, R.S.O. 1990, c. C.30.\n"
            "(b) Within seven (7) days of receiving payment from the Owner, the "
            "Contractor shall pay each sub-contractor for amounts attributable to that "
            "sub-contractor's work.\n"
            "(c) Either party may refer any dispute to interim adjudication under "
            "Part II.1 of the Construction Act. The adjudicator's determination is "
            "binding on an interim basis and enforceable in the same manner as a court "
            "order. The merits of the dispute may be subsequently determined by "
            "litigation or arbitration."
        ),
        "guidance_note": (
            "Map invoice and payment milestones to the 28/7-day windows. Designate an "
            "internal contact for adjudication notices and ensure the Authorized "
            "Nominating Authority's roster is referenced."
        ),
        "source": "ON_PROCUREMENT_ACT",
        "source_ref": "Construction Act, R.S.O. 1990, c. C.30, Parts I.1 and II.1",
        "source_url": "https://www.ontario.ca/laws/statute/90c30",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["Ontario", "Construction Act", "prompt payment", "adjudication"],
        "related_article_ids": ["ON-CON-CLAUSE-CCDC-FORMS-017"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # CCDC standard contract forms
    # =================================================================
    {
        "article_id": "ANY-CON-CLAUSE-CCDC-FORMS-017",
        "jurisdiction_code": None,
        "commodity_category_code": "CON_BUILDING",
        "commodity_subcategory_code": None,
        "article_type": "template_language",
        "procurement_phase": "sow_drafting",
        "section_type": "terms_conditions",
        "title": "Use of CCDC Standard Construction Contract Forms",
        "title_fr": "Recours aux formules contractuelles normalisées CCDC",
        "content": (
            "The Canadian Construction Documents Committee publishes industry-consensus "
            "contract forms that are the de facto standard across Canada: CCDC 2 "
            "(stipulated price), CCDC 5A (construction management for services), CCDC 5B "
            "(CM-at-risk), CCDC 14 (design-build), CCDC 17 (sole-source service), "
            "CCDC 23 (qualifications-based selection guide), and CCDC 31 (architect/"
            "engineer services). Use of these forms reduces drafting risk and bid challenge "
            "exposure because terms are well-understood across the industry."
        ),
        "template_text": (
            "Form of Contract. The Contract shall be in the form of {CCDC 2 / CCDC 5B / "
            "CCDC 14 / CCDC 31 — 2020 edition} as published by the Canadian Construction "
            "Documents Committee, modified only by the supplementary conditions in "
            "Appendix A. In the event of conflict between CCDC general conditions and "
            "the supplementary conditions, the supplementary conditions prevail."
        ),
        "guidance_note": (
            "CCDC documents must be obtained as serial-numbered originals and bear the "
            "CCDC seal — photocopied or unsealed forms are not enforceable as CCDC "
            "documents."
        ),
        "source": "CCDC",
        "source_ref": "CCDC Standard Documents (2020 editions)",
        "source_url": "https://www.ccdc.org/",
        "is_mandatory": False,
        "importance": "high",
        "risk_if_omitted": "medium",
        "applies_above_value_cad": 100000.0,
        "applies_to_methods": ["RFP", "ITT", "DESIGN_BUILD"],
        "tags": ["CCDC", "construction", "contract form"],
        "related_article_ids": ["ON-CON-CLAUSE-PROMPT-PAYMENT-016", "ANY-CON-CLAUSE-PERFORMANCE-BOND-018"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # Construction performance / labour-and-material bonds
    # =================================================================
    {
        "article_id": "ANY-CON-MANDATORY-PERFORMANCE-BOND-018",
        "jurisdiction_code": None,
        "commodity_category_code": "CON_BUILDING",
        "commodity_subcategory_code": None,
        "article_type": "mandatory_req",
        "procurement_phase": "solicitation",
        "section_type": "mandatory_requirements",
        "title": "Performance and Labour & Material Payment Bonds",
        "title_fr": "Cautionnement d'exécution et de paiement de la main-d'œuvre et des matériaux",
        "content": (
            "Construction contracts above prescribed thresholds typically require both "
            "a Performance Bond (50% of contract value) and a Labour & Material Payment "
            "Bond (50% of contract value), each issued by a surety licensed in Canada. "
            "The bonds back the Contractor's obligations to complete the work and to pay "
            "sub-contractors and material suppliers."
        ),
        "template_text": (
            "Bonding. Within ten (10) Business Days of Contract execution and prior to "
            "commencement of the Work, the Contractor shall provide to the Owner: "
            "(a) a Performance Bond in the amount of fifty percent (50%) of the "
            "Contract Price; and (b) a Labour and Material Payment Bond in the amount "
            "of fifty percent (50%) of the Contract Price; each in the form prescribed "
            "by CCDC 220-2002, issued by a surety licensed by the Office of the "
            "Superintendent of Financial Institutions and acceptable to the Owner."
        ),
        "guidance_note": (
            "For very large or higher-risk projects, consider 100% performance bonds "
            "or alternative security (letters of credit). Bid bonds (typically 10%) are "
            "addressed separately at solicitation stage."
        ),
        "source": "CCDC",
        "source_ref": "CCDC 220-2002 Performance Bond / Labour and Material Payment Bond",
        "source_url": "https://www.ccdc.org/",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "critical",
        "applies_above_value_cad": 500000.0,
        "applies_to_methods": ["ITT", "RFP"],
        "tags": ["bonding", "construction", "performance bond"],
        "related_article_ids": ["ANY-CON-CLAUSE-CCDC-FORMS-017"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # Termination for convenience (universal)
    # =================================================================
    {
        "article_id": "ANY-ANY-CLAUSE-TERMINATION-CONV-019",
        "jurisdiction_code": None,
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "sow_drafting",
        "section_type": "terms_conditions",
        "title": "Termination for Convenience",
        "title_fr": "Résiliation pour des raisons de commodité",
        "content": (
            "Public-sector contracts customarily include a termination-for-convenience "
            "right exercisable on written notice, with the contractor's recovery limited "
            "to costs incurred to the date of termination plus a reasonable allowance "
            "for demobilisation. Excluded heads of claim are anticipated profit on "
            "unperformed work and consequential damages."
        ),
        "template_text": (
            "Termination for Convenience.\n"
            "(a) The Public Body may, at any time, terminate this Contract in whole or "
            "in part for any reason on thirty (30) days' written notice to the Contractor.\n"
            "(b) Upon receipt of the notice, the Contractor shall: (i) cease work as "
            "directed; (ii) place no further sub-contracts or orders; (iii) terminate or "
            "assign sub-contracts as directed; and (iv) preserve and protect Public Body "
            "property in its custody.\n"
            "(c) The Public Body shall pay the Contractor: (i) the Contract Price for "
            "Work satisfactorily performed and accepted up to the date of termination; "
            "(ii) reasonable demobilisation costs; and (iii) non-cancellable third-party "
            "commitments approved by the Contracting Authority. The Contractor shall not "
            "be entitled to anticipated profit on unperformed Work or to indirect, "
            "consequential, or special damages of any kind."
        ),
        "guidance_note": (
            "Pair with a separate termination-for-cause clause covering material breach. "
            "Avoid letting the for-cause notice and cure period make termination for "
            "convenience the de facto only option."
        ),
        "source": "SACC",
        "source_ref": "PSPC SACC General Conditions — Termination for Convenience",
        "source_url": "https://buyandsell.gc.ca/policy-and-guidelines/standard-acquisition-clauses-and-conditions-manual",
        "is_mandatory": False,
        "importance": "high",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["termination", "convenience", "exit"],
        "related_article_ids": ["ANY-ANY-CLAUSE-LIMIT-LIABILITY-PROV-020"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # Provincial limitation of liability (non-federal)
    # =================================================================
    {
        "article_id": "ANY-ANY-CLAUSE-LIMIT-LIABILITY-PROV-020",
        "jurisdiction_code": None,
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "sow_drafting",
        "section_type": "terms_conditions",
        "title": "Limitation of Liability — Provincial / BPS Default",
        "title_fr": "Limitation de responsabilité — défaut provincial / SPL",
        "content": (
            "Provincial and BPS sector contracts typically cap the supplier's aggregate "
            "liability at the greater of the contract value or a fixed dollar floor "
            "(commonly $1M–$5M depending on risk profile), with carve-outs mirroring "
            "federal practice."
        ),
        "template_text": (
            "Limitation of Liability.\n"
            "(a) Subject to paragraph (b), each party's total aggregate liability for "
            "any claim arising out of or relating to this Contract is limited to the "
            "greater of (i) the total fees paid or payable under this Contract; or (ii) "
            "${LIMIT_FLOOR_CAD} CAD.\n"
            "(b) The limit in paragraph (a) does not apply to: (i) bodily injury or "
            "property damage caused by negligence or wilful misconduct; (ii) IP "
            "infringement indemnification; (iii) breach of confidentiality or privacy "
            "obligations; or (iv) fraud.\n"
            "(c) Neither party shall be liable for indirect, incidental, consequential, "
            "or punitive damages, including lost profits or lost data, except as "
            "provided in paragraph (b)."
        ),
        "guidance_note": (
            "Tune the floor to risk: $1M is acceptable for low-value commodity buys; "
            "raise to $5M+ for projects with high data, safety, or reputational exposure."
        ),
        "source": "BPS_DIRECTIVE",
        "source_ref": "BPS Procurement Directive standard terms; provincial variants",
        "source_url": None,
        "is_mandatory": False,
        "importance": "high",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["liability", "limitation", "provincial"],
        "related_article_ids": ["FED-ANY-CLAUSE-LIMIT-LIABILITY-003"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # SLA: IT services KPI examples
    # =================================================================
    {
        "article_id": "ANY-IT_DIGITAL-SLA-AVAILABILITY-021",
        "jurisdiction_code": None,
        "commodity_category_code": "IT_CLOUD",
        "commodity_subcategory_code": None,
        "article_type": "sla_kpi",
        "procurement_phase": "contract_management",
        "section_type": "sla",
        "title": "Availability KPI with Service Credits — Cloud / Managed IT",
        "title_fr": "ICP de disponibilité avec crédits de service — TI gérée / nuage",
        "content": (
            "An availability SLA of 99.9% (\"three nines\", ≈8.76 hours of unplanned "
            "downtime per year) is a common floor for production cloud and managed IT "
            "services. Service credits create an enforceable, no-fault remedy for "
            "missed targets and avoid having to prove damages."
        ),
        "template_text": (
            "Service Availability KPI.\n"
            "Target: ≥ 99.9% monthly availability of the Production Service, measured "
            "as (Total Minutes − Excluded Minutes − Unavailable Minutes) ÷ "
            "(Total Minutes − Excluded Minutes).\n"
            "Excluded Minutes: pre-approved scheduled maintenance windows, force majeure, "
            "and downtime caused by acts or omissions of the Public Body.\n"
            "Service Credits: 5% of monthly fees if availability is < 99.9% but ≥ 99.0%; "
            "10% if < 99.0% but ≥ 98.0%; 25% if < 98.0%. Service credits are the "
            "Public Body's sole financial remedy for availability failures, subject to "
            "the Termination for Cause right that arises after three consecutive months "
            "below 98.0%."
        ),
        "guidance_note": (
            "Tier the credits to actually move the needle — flat 5% credits do not "
            "incentivise the supplier. Always pair with a termination-for-cause "
            "trigger so the credits do not become a liability cap."
        ),
        "source": "INDUSTRY_PRACTICE",
        "source_ref": "Common in PSPC EN578-200067/E SaaS SAs and Ontario VOR IT contracts",
        "source_url": None,
        "is_mandatory": False,
        "importance": "high",
        "risk_if_omitted": "medium",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["SLA", "availability", "service credits", "KPI"],
        "related_article_ids": ["ANY-IT_DIGITAL-SLA-INCIDENT-022"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # SLA: Incident response KPI
    # =================================================================
    {
        "article_id": "ANY-IT_DIGITAL-SLA-INCIDENT-022",
        "jurisdiction_code": None,
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "sla_kpi",
        "procurement_phase": "contract_management",
        "section_type": "sla",
        "title": "Incident Response & Resolution KPIs",
        "title_fr": "ICP de réponse et de résolution aux incidents",
        "content": (
            "Standard severity-based incident KPIs cover both response (acknowledgement) "
            "and resolution targets. Tying both to the contract gives the Public Body a "
            "remedy for ticket-handling delays even when overall availability remains "
            "within target."
        ),
        "template_text": (
            "Incident Response and Resolution KPIs.\n"
            "Severity 1 (service down, no workaround): response within 15 minutes; "
            "resolution within 4 hours.\n"
            "Severity 2 (service degraded or major function unavailable): response within "
            "30 minutes; resolution within 8 hours.\n"
            "Severity 3 (minor function unavailable, workaround exists): response within "
            "2 hours; resolution within 2 Business Days.\n"
            "Severity 4 (cosmetic, documentation, enhancement): response within 1 "
            "Business Day; resolution within next release cycle.\n"
            "Service credits: 5% of monthly fees for each unmet Severity-1 KPI, capped at "
            "25% per month. Three Severity-1 misses in a rolling 90-day window trigger "
            "the Public Body's right to require a remediation plan."
        ),
        "guidance_note": (
            "Define each severity level with concrete examples in the SOW so triage "
            "disagreements do not consume the entire SLA."
        ),
        "source": "INDUSTRY_PRACTICE",
        "source_ref": "Common SLA practice; aligned with ITIL incident-management taxonomy",
        "source_url": None,
        "is_mandatory": False,
        "importance": "high",
        "risk_if_omitted": "medium",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["SLA", "incident", "response", "resolution"],
        "related_article_ids": ["ANY-IT_DIGITAL-SLA-AVAILABILITY-021"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # Acceptance criteria — generic
    # =================================================================
    {
        "article_id": "ANY-ANY-CLAUSE-ACCEPTANCE-023",
        "jurisdiction_code": None,
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "acceptance_criteria",
        "procurement_phase": "acceptance",
        "section_type": "acceptance_criteria",
        "title": "Deliverable Acceptance and Cure",
        "title_fr": "Acceptation des livrables et délai de correction",
        "content": (
            "Acceptance criteria should be objective, testable, and tied to written "
            "deliverable specifications. A defined review window, cure period, and "
            "deemed-acceptance default protect both parties from ambiguous sign-off."
        ),
        "template_text": (
            "Deliverable Acceptance.\n"
            "(a) The Contractor shall deliver each Deliverable identified in Schedule B "
            "in accordance with the acceptance criteria stated for that Deliverable.\n"
            "(b) Within fifteen (15) Business Days of receipt, the Public Body shall "
            "either accept the Deliverable in writing or provide a written list of "
            "deficiencies. Silence at the end of fifteen (15) Business Days constitutes "
            "deemed acceptance.\n"
            "(c) Upon receipt of a deficiency notice, the Contractor shall, at its sole "
            "cost, cure the deficiencies and re-submit the Deliverable within ten (10) "
            "Business Days, after which the review process in (b) re-applies.\n"
            "(d) Three rejections of the same Deliverable for the same deficiency are a "
            "material breach entitling the Public Body to terminate the Contract for "
            "cause."
        ),
        "guidance_note": (
            "Pair each Deliverable in Schedule B with one to three measurable acceptance "
            "criteria. Vague criteria (\"to the Public Body's satisfaction\") create "
            "disputes."
        ),
        "source": "SACC",
        "source_ref": "PSPC SACC General Conditions; broad public-sector convention",
        "source_url": None,
        "is_mandatory": False,
        "importance": "high",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["acceptance", "deliverables", "cure"],
        "related_article_ids": [],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # Pricing — Time and Materials with cap
    # =================================================================
    {
        "article_id": "ANY-PROF_SVC-CLAUSE-PRICING-TM-024",
        "jurisdiction_code": None,
        "commodity_category_code": "PROF_MGMT_CONSULTING",
        "commodity_subcategory_code": None,
        "article_type": "pricing_guidance",
        "procurement_phase": "sow_drafting",
        "section_type": "pricing",
        "title": "Time-and-Materials Pricing with Not-to-Exceed Ceiling",
        "title_fr": "Tarification temps et matériel avec plafond",
        "content": (
            "Where scope is uncertain, T&M pricing with a hard not-to-exceed ceiling "
            "balances flexibility against cost control. The supplier bills hourly against "
            "a fixed rate card; the Public Body monitors burn rate against the ceiling "
            "and authorises further work via written task authorisations."
        ),
        "template_text": (
            "Time-and-Materials Pricing.\n"
            "(a) Fees for services rendered shall be calculated by multiplying actual "
            "hours worked, recorded to the nearest tenth of an hour, by the fixed rates "
            "set out in Schedule C (Rate Card).\n"
            "(b) Total fees plus authorised expenses shall not exceed ${CEILING_CAD} CAD "
            "(the \"Not-to-Exceed Ceiling\") without a written amendment to this Contract "
            "executed by the Contracting Authority.\n"
            "(c) The Contractor shall provide a monthly burn-rate report identifying "
            "hours billed by resource and remaining ceiling. When 75% of the Ceiling is "
            "consumed, the Contractor shall promptly notify the Contracting Authority and "
            "propose ceiling-management options."
        ),
        "guidance_note": (
            "Always lock the rate card for the entire term — re-pricing mid-contract "
            "voids the cost-control benefit. Combine with task authorisation forms (TAFs) "
            "for finer scope control."
        ),
        "source": "INDUSTRY_PRACTICE",
        "source_ref": "PSPC professional-services SAs (e.g., TBIPS, ProServices)",
        "source_url": "https://buyandsell.gc.ca/professional-services",
        "is_mandatory": False,
        "importance": "medium",
        "risk_if_omitted": "medium",
        "applies_above_value_cad": None,
        "applies_to_methods": ["RFP", "RFSO"],
        "tags": ["pricing", "T&M", "ceiling", "rate card"],
        "related_article_ids": [],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # Conflict of Interest declaration
    # =================================================================
    {
        "article_id": "ANY-ANY-MANDATORY-CONFLICT-OF-INTEREST-025",
        "jurisdiction_code": None,
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "mandatory_req",
        "procurement_phase": "solicitation",
        "section_type": "mandatory_requirements",
        "title": "Conflict-of-Interest and Code of Conduct Declarations",
        "title_fr": "Déclarations de conflit d'intérêts et de code de conduite",
        "content": (
            "Public-sector solicitations require bidders to declare any actual, "
            "potential, or perceived conflicts of interest, and to acknowledge the "
            "applicable Code of Conduct (e.g., PSPC Code of Conduct for Procurement, "
            "Ontario Public Service Procurement Ethical Standard). Failure to disclose "
            "is a basis for bid disqualification and contract cancellation."
        ),
        "template_text": (
            "Conflict of Interest. The Bidder declares that, except as disclosed in "
            "writing in Schedule D: (i) no individual involved in preparing the Bid has "
            "a relationship with any official of the Public Body that could compromise "
            "the integrity of the procurement; (ii) no Bidder employee is the spouse, "
            "common-law partner, or close family member of any such official; and "
            "(iii) the Bidder has not retained or compensated any current or former "
            "official of the Public Body in respect of this procurement.\n"
            "Code of Conduct. The Bidder acknowledges and agrees to comply with the "
            "{PSPC Code of Conduct for Procurement / Ontario Procurement Ethical "
            "Standard}, including its prohibitions on collusion, bid rigging, and "
            "improper communications during the standstill period."
        ),
        "guidance_note": (
            "Maintain a live evaluation-team COI register; have evaluators re-confirm "
            "no-conflict at each consensus meeting."
        ),
        "source": "TB_POLICY",
        "source_ref": "PSPC Code of Conduct for Procurement; Ontario Procurement Ethical Standard",
        "source_url": "https://buyandsell.gc.ca/policy-and-guidelines/standard-procurement-documents/code-of-conduct-for-procurement",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "critical",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["conflict of interest", "ethics", "code of conduct"],
        "related_article_ids": [],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # AODA — Ontario digital accessibility
    # =================================================================
    {
        "article_id": "ON-IT_DIGITAL-CLAUSE-AODA-026",
        "jurisdiction_code": "ON",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "regulatory_requirement",
        "procurement_phase": "sow_drafting",
        "section_type": "acceptance_criteria",
        "title": "AODA / IASR Information & Communications Standards",
        "title_fr": "LAPHO / RNAS — normes d'information et de communication",
        "content": (
            "Ontario's Accessibility for Ontarians with Disabilities Act and the "
            "Integrated Accessibility Standards Regulation (O. Reg. 191/11) require "
            "websites, web content, and many digital resources to conform to WCAG 2.0 "
            "Level AA, with AAA encouraged where feasible. The BPS Procurement Directive "
            "requires accessibility considerations to be built into procurement criteria."
        ),
        "template_text": (
            "AODA Conformance. All web content and digital deliverables shall conform to "
            "WCAG 2.0 Level AA in accordance with O. Reg. 191/11 (Integrated Accessibility "
            "Standards). Where higher conformance is reasonably achievable, the Contractor "
            "shall pursue WCAG 2.1 Level AA. The Contractor shall remedy at its sole "
            "expense any conformance failures identified in user-acceptance testing."
        ),
        "guidance_note": (
            "Ontario's standard is WCAG 2.0 AA by regulation; many BPS organisations "
            "specify WCAG 2.1 AA contractually to align with federal practice."
        ),
        "source": "ON_PROCUREMENT_ACT",
        "source_ref": "Accessibility for Ontarians with Disabilities Act, 2005; O. Reg. 191/11",
        "source_url": "https://www.ontario.ca/laws/regulation/110191",
        "is_mandatory": True,
        "importance": "high",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["AODA", "WCAG", "accessibility", "Ontario"],
        "related_article_ids": ["FED-IT_DIGITAL-CLAUSE-ACCESSIBILITY-012"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # BC — FOIPPA data residency for personal information
    # =================================================================
    {
        "article_id": "BC-ANY-COMPLIANCE-FOIPPA-DATA-027",
        "jurisdiction_code": "BC",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "regulatory_requirement",
        "procurement_phase": "sow_drafting",
        "section_type": "mandatory_requirements",
        "title": "BC FOIPPA — Personal Information Storage Requirements",
        "title_fr": "FOIPPA (C.-B.) — exigences de stockage des renseignements personnels",
        "content": (
            "British Columbia's Freedom of Information and Protection of Privacy Act "
            "(FOIPPA) historically required personal information in custody or control "
            "of a public body to be stored only in Canada. Following 2021 amendments, "
            "outside-of-Canada storage is now permitted but only with privacy-protective "
            "controls. Contractors must support PIA, breach-notification, and disclosure-"
            "of-cross-border-flows requirements."
        ),
        "template_text": (
            "FOIPPA Personal Information.\n"
            "(a) The Contractor shall, in collecting, using, disclosing, retaining, and "
            "destroying Personal Information for the Public Body, comply with the "
            "Freedom of Information and Protection of Privacy Act (RSBC 1996, c. 165) "
            "and any directives issued by the Office of the Information and Privacy "
            "Commissioner of British Columbia.\n"
            "(b) The Contractor shall co-operate in the completion of a Privacy Impact "
            "Assessment, shall implement the privacy-protective controls identified in "
            "the PIA, and shall not store, access, or disclose Personal Information "
            "outside Canada except as expressly authorised by the Public Body in writing.\n"
            "(c) The Contractor shall notify the Public Body within 24 hours of any "
            "actual or suspected privacy breach, including unauthorised cross-border "
            "access to Personal Information."
        ),
        "guidance_note": (
            "Even after the 2021 amendments, conservative practice for sensitive personal "
            "information (health, child welfare, indigenous data) is to require Canadian-"
            "only storage. Confirm with the BC OIPC's current guidance before relaxing."
        ),
        "source": "BC_LEGISLATION",
        "source_ref": "Freedom of Information and Protection of Privacy Act (RSBC 1996, c. 165)",
        "source_url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96165_00",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["FOIPPA", "BC", "data residency", "privacy"],
        "related_article_ids": ["FED-IT_CLOUD-CLAUSE-DATA-RESIDENCY-001"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # Quebec — Charter of French Language
    # =================================================================
    {
        "article_id": "QC-ANY-COMPLIANCE-FRENCH-LANGUAGE-028",
        "jurisdiction_code": "QC",
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "regulatory_requirement",
        "procurement_phase": "sow_drafting",
        "section_type": "mandatory_requirements",
        "title": "Charter of the French Language — Quebec Public Bodies",
        "title_fr": "Charte de la langue française — organismes publics québécois",
        "content": (
            "Quebec's Charter of the French Language requires that the language of public "
            "administration is French. Contracts entered into with public bodies, "
            "supporting documents, and deliverables intended for the public administration "
            "or the public must be in French; English versions may accompany but do not "
            "displace the French-language requirement."
        ),
        "template_text": (
            "Language. This Contract is drawn up in French. All deliverables, documents, "
            "communications and software interfaces produced for or used by the Public "
            "Body shall be in French. Where the Contractor produces a translation for "
            "the convenience of its personnel or other parties, the French version "
            "remains the authoritative version. Bilingual deliverables are permitted "
            "provided that the French text appears at least as prominently as any other "
            "language."
        ),
        "guidance_note": (
            "Recent amendments (Bill 96) have tightened the language regime — confirm "
            "with the Office québécois de la langue française where in doubt."
        ),
        "source": "QC_LEGISLATION",
        "source_ref": "Charter of the French Language, CQLR c. C-11",
        "source_url": "https://www.legisquebec.gouv.qc.ca/en/document/cs/C-11",
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["Quebec", "Charter of the French Language", "language"],
        "related_article_ids": ["FED-ANY-CLAUSE-OFFICIAL-LANGUAGES-007"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # Insurance — generic CGL + professional liability
    # =================================================================
    {
        "article_id": "ANY-ANY-MANDATORY-INSURANCE-029",
        "jurisdiction_code": None,
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "mandatory_req",
        "procurement_phase": "solicitation",
        "section_type": "mandatory_requirements",
        "title": "Insurance — Commercial General Liability and Professional Liability",
        "title_fr": "Assurances — responsabilité civile générale et professionnelle",
        "content": (
            "Standard public-sector insurance requirements include Commercial General "
            "Liability ($2M–$5M per occurrence), Automobile Liability where contractor "
            "vehicles are used, and Professional Liability / Errors & Omissions ($1M–"
            "$5M) for advisory and design services. Cyber Liability ($2M+) is "
            "increasingly required for IT and data-handling work."
        ),
        "template_text": (
            "Insurance. Throughout the term of this Contract and for two (2) years "
            "thereafter, the Contractor shall maintain, at its own cost, the following "
            "insurance with insurers licensed in Canada:\n"
            "(a) Commercial General Liability — minimum $5,000,000 per occurrence, "
            "naming the Public Body as additional insured, including bodily injury, "
            "property damage, products and completed operations, contractual liability, "
            "and a cross-liability or severability of interests endorsement;\n"
            "(b) Professional Liability / Errors & Omissions — minimum $2,000,000 per "
            "claim, on a claims-made basis, with a discovery period of at least 24 months;\n"
            "(c) Cyber Liability — minimum $2,000,000 per claim, where the Contract "
            "involves access to personal information or operational technology;\n"
            "(d) Automobile Liability — $2,000,000 inclusive limit on any vehicle used in "
            "the performance of the Contract.\n"
            "Certificates of insurance shall be provided prior to commencement of Work "
            "and on request thereafter."
        ),
        "guidance_note": (
            "Calibrate limits to project risk: $5M CGL is a public-sector floor; $10M+ "
            "for construction or large data engagements. Always require notice-of-"
            "cancellation endorsements (30 days)."
        ),
        "source": "INDUSTRY_PRACTICE",
        "source_ref": "PSPC standard insurance schedule; provincial public-body templates",
        "source_url": None,
        "is_mandatory": True,
        "importance": "critical",
        "risk_if_omitted": "critical",
        "applies_above_value_cad": 25000.0,
        "applies_to_methods": None,
        "tags": ["insurance", "CGL", "professional liability", "cyber"],
        "related_article_ids": ["ANY-ANY-CLAUSE-LIMIT-LIABILITY-PROV-020"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # Transition-out
    # =================================================================
    {
        "article_id": "ANY-ANY-CLAUSE-TRANSITION-OUT-030",
        "jurisdiction_code": None,
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "closeout",
        "section_type": "transition",
        "title": "Transition-Out Assistance and Knowledge Transfer",
        "title_fr": "Transition de sortie et transfert de connaissances",
        "content": (
            "Public-sector contracts should always include a transition-out clause "
            "obligating the contractor to assist a successor (or the Public Body itself) "
            "in resuming the work without disruption. Pricing for transition-out should "
            "be locked at award; otherwise, the Public Body has no leverage to compel "
            "co-operation at the end of the term."
        ),
        "template_text": (
            "Transition-Out.\n"
            "(a) Beginning ninety (90) days before the end of the Term (or upon notice "
            "of termination), the Contractor shall provide transition assistance to "
            "the Public Body or its designated successor.\n"
            "(b) Transition assistance shall include: knowledge-transfer sessions; "
            "documentation of all run-time procedures, configurations, and credentials; "
            "delivery of source code, data extracts, and operational artifacts in their "
            "native formats; and reasonable on-site or remote support during cut-over.\n"
            "(c) Transition assistance up to ten percent (10%) of the original Contract "
            "Price shall be provided at no additional charge. Effort beyond that ceiling "
            "shall be billed at the Schedule C rates.\n"
            "(d) The Contractor shall not, by any act or omission, impede or delay the "
            "transition. Hostile transition activity is a material breach giving rise to "
            "termination for cause and damages."
        ),
        "guidance_note": (
            "The 10% no-charge floor is conventional for IT services; adjust upward for "
            "complex or data-heavy engagements."
        ),
        "source": "INDUSTRY_PRACTICE",
        "source_ref": "Common in PSPC IT services SAs and Ontario VOR contracts",
        "source_url": None,
        "is_mandatory": False,
        "importance": "high",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["transition", "exit", "knowledge transfer"],
        "related_article_ids": ["ANY-ANY-CLAUSE-TERMINATION-CONV-019"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # Indemnity — IP infringement
    # =================================================================
    {
        "article_id": "ANY-ANY-CLAUSE-IP-INDEMNITY-031",
        "jurisdiction_code": None,
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "sow_drafting",
        "section_type": "terms_conditions",
        "title": "IP Infringement Indemnity",
        "title_fr": "Indemnisation pour contrefaçon de propriété intellectuelle",
        "content": (
            "An IP infringement indemnity is one of the few uncapped exposure points "
            "in a well-drafted contract. The supplier defends and indemnifies the Public "
            "Body for third-party claims that the deliverables infringe Canadian IP "
            "rights, with a duty to procure a licence, modify the deliverable, or refund "
            "the fees if it cannot continue."
        ),
        "template_text": (
            "Intellectual Property Indemnity.\n"
            "(a) The Contractor shall defend, indemnify and hold harmless the Public "
            "Body, its officers, employees and agents from any third-party claim that "
            "any Deliverable, or the use of any Deliverable in accordance with this "
            "Contract, infringes any Canadian copyright, patent, trademark, or trade "
            "secret right.\n"
            "(b) Upon notice of any such claim, the Contractor shall, at its option and "
            "sole expense: (i) procure for the Public Body the right to continue using "
            "the affected Deliverable; (ii) replace or modify it to be non-infringing "
            "while preserving substantially equivalent functionality; or (iii) accept "
            "return of the Deliverable and refund all fees paid for it.\n"
            "(c) This indemnity does not apply to the extent the claim arises from the "
            "Public Body's modification of the Deliverable or its combination with "
            "non-Contractor materials not contemplated by this Contract."
        ),
        "guidance_note": (
            "Open-source software has nuanced indemnity issues — many suppliers exclude "
            "OSS components entirely. Negotiate a reduced indemnity (e.g., procure-or-"
            "refund) rather than allowing a complete OSS carve-out."
        ),
        "source": "INDUSTRY_PRACTICE",
        "source_ref": "PSPC SACC General Conditions; common across Canadian public-sector contracts",
        "source_url": None,
        "is_mandatory": False,
        "importance": "critical",
        "risk_if_omitted": "high",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["IP", "indemnity", "infringement"],
        "related_article_ids": ["FED-ANY-CLAUSE-IP-OWNERSHIP-004", "FED-ANY-CLAUSE-LIMIT-LIABILITY-003"],
        "version": "1.0",
        "is_active": True,
    },

    # =================================================================
    # Force Majeure (modern, including pandemic)
    # =================================================================
    {
        "article_id": "ANY-ANY-CLAUSE-FORCE-MAJEURE-032",
        "jurisdiction_code": None,
        "commodity_category_code": None,
        "commodity_subcategory_code": None,
        "article_type": "clause",
        "procurement_phase": "sow_drafting",
        "section_type": "terms_conditions",
        "title": "Force Majeure",
        "title_fr": "Force majeure",
        "content": (
            "Modern force-majeure clauses explicitly enumerate pandemics, declared "
            "public-health emergencies, cyber-attacks, and supply-chain disruptions, and "
            "set out an objective threshold (cumulative event days) beyond which either "
            "party may terminate without further liability."
        ),
        "template_text": (
            "Force Majeure.\n"
            "(a) Neither party is liable for any failure or delay caused by a Force "
            "Majeure Event, defined as an event beyond the reasonable control of the "
            "affected party, including acts of God, war, civil unrest, declared "
            "pandemics, public-health emergencies of provincial or national scope, "
            "wide-area cyber-attack, governmental orders, and labour disputes not arising "
            "from the affected party's own actions.\n"
            "(b) The affected party shall promptly notify the other in writing, use "
            "reasonable efforts to mitigate, and resume performance as soon as the Force "
            "Majeure Event abates.\n"
            "(c) If the Force Majeure Event continues for more than sixty (60) "
            "consecutive days, either party may terminate this Contract on ten (10) "
            "days' written notice, with the Contractor compensated for Work satisfactorily "
            "performed up to the date of termination as set out in the Termination for "
            "Convenience clause."
        ),
        "guidance_note": (
            "Resist asymmetric force-majeure language that benefits only the supplier — "
            "the public body should also enjoy relief from corresponding obligations."
        ),
        "source": "INDUSTRY_PRACTICE",
        "source_ref": "PSPC SACC General Conditions; modern post-COVID drafting practice",
        "source_url": None,
        "is_mandatory": False,
        "importance": "high",
        "risk_if_omitted": "medium",
        "applies_above_value_cad": None,
        "applies_to_methods": None,
        "tags": ["force majeure", "pandemic", "cyber"],
        "related_article_ids": ["ANY-ANY-CLAUSE-TERMINATION-CONV-019"],
        "version": "1.0",
        "is_active": True,
    },
]
