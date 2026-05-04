# Canadian Government Procurement — Jurisdiction & Framework Seed Data
# Source references: CFTA (2017), FAA R.S.C. 1985 c. F-11, PSPC Supply Manual,
# CUSMA Chapter 13, CETA Chapter 19, provincial legislation as noted.
# Thresholds as of 2024; CFTA thresholds indexed annually.

JURISDICTIONS = [
    {
        "code": "FED",
        "name": "Government of Canada (Federal)",
        "name_fr": "Gouvernement du Canada (fédéral)",
        "jtype": "federal",
        "trade_agreements": ["CFTA", "CUSMA", "CETA", "CPTPP", "WTO-GPA"],
        "procurement_portal_url": "https://buyandsell.gc.ca",
        "legislation_name": "Financial Administration Act (FAA) / Government Contracts Regulations",
        "legislation_url": "https://laws-lois.justice.gc.ca/eng/acts/F-11/",
        "requires_bilingual": True,
        "has_indigenous_set_aside": True,  # Procurement Strategy for Indigenous Business (PSIB)
        "nwpta_member": False,
    },
    {
        "code": "ON",
        "name": "Ontario",
        "name_fr": "Ontario",
        "jtype": "province",
        "trade_agreements": ["CFTA"],
        "procurement_portal_url": "https://ontariotenders.ca",
        "legislation_name": "Ontario Procurement Act, 2019 / BPS Procurement Directive",
        "legislation_url": "https://www.ontario.ca/laws/statute/19p07",
        "requires_bilingual": False,
        "has_indigenous_set_aside": True,
        "nwpta_member": False,
    },
    {
        "code": "BC",
        "name": "British Columbia",
        "name_fr": "Colombie-Britannique",
        "jtype": "province",
        "trade_agreements": ["CFTA", "NWPTA"],
        "procurement_portal_url": "https://www.bcbid.gov.bc.ca",
        "legislation_name": "Procurement Services Act (SBC 2003, c. 22)",
        "legislation_url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/03022_01",
        "requires_bilingual": False,
        "has_indigenous_set_aside": True,
        "nwpta_member": True,
    },
    {
        "code": "AB",
        "name": "Alberta",
        "name_fr": "Alberta",
        "jtype": "province",
        "trade_agreements": ["CFTA", "NWPTA"],
        "procurement_portal_url": "https://www.merx.com/Alberta",
        "legislation_name": "Government Organization Act / Supply Chain Management Policy",
        "legislation_url": "https://www.qp.alberta.ca/documents/acts/G10.pdf",
        "requires_bilingual": False,
        "has_indigenous_set_aside": True,
        "nwpta_member": True,
    },
    {
        "code": "QC",
        "name": "Quebec",
        "name_fr": "Québec",
        "jtype": "province",
        "trade_agreements": ["CFTA"],
        "procurement_portal_url": "https://seao.ca",
        "legislation_name": "Act Respecting Contracts of Public Bodies (CQLR c. C-65.1)",
        "legislation_url": "https://www.legisquebec.gouv.qc.ca/en/document/cs/C-65.1",
        "requires_bilingual": False,  # French required per Charter of the French Language; not bilingual
        "has_indigenous_set_aside": False,
        "nwpta_member": False,
    },
    {
        "code": "SK",
        "name": "Saskatchewan",
        "name_fr": "Saskatchewan",
        "jtype": "province",
        "trade_agreements": ["CFTA", "NWPTA"],
        "procurement_portal_url": "https://www.saskpurchasing.gov.sk.ca",
        "legislation_name": "Government Administration Act (SS 2014, c. G-5.01)",
        "legislation_url": "https://publications.saskatchewan.ca/#/products/70732",
        "requires_bilingual": False,
        "has_indigenous_set_aside": True,
        "nwpta_member": True,
    },
    {
        "code": "MB",
        "name": "Manitoba",
        "name_fr": "Manitoba",
        "jtype": "province",
        "trade_agreements": ["CFTA"],
        "procurement_portal_url": "https://www.gov.mb.ca/tenders/",
        "legislation_name": "Materials Management Policy / The Financial Administration Act (CCSM c. F55)",
        "legislation_url": "https://web2.gov.mb.ca/laws/statutes/ccsm/f055e.php",
        "requires_bilingual": False,
        "has_indigenous_set_aside": True,
        "nwpta_member": False,  # Manitoba is NOT a NWPTA member
    },
    {
        "code": "NB",
        "name": "New Brunswick",
        "name_fr": "Nouveau-Brunswick",
        "jtype": "province",
        "trade_agreements": ["CFTA"],
        "procurement_portal_url": "https://nbtenders.ca",
        "legislation_name": "Procurement Act (SNB 2012, c. 12)",
        "legislation_url": "https://laws.gnb.ca/en/ShowPdf/cs/P-22.4.pdf",
        "requires_bilingual": True,  # Official Languages Act — NB is officially bilingual
        "has_indigenous_set_aside": False,
        "nwpta_member": False,
    },
    {
        "code": "NS",
        "name": "Nova Scotia",
        "name_fr": "Nouvelle-Écosse",
        "jtype": "province",
        "trade_agreements": ["CFTA"],
        "procurement_portal_url": "https://novascotia.ca/tenders/",
        "legislation_name": "Nova Scotia Procurement Act (SNS 2011, c. 12)",
        "legislation_url": "https://nslegislature.ca/sites/default/files/legc/statutes/procurement.pdf",
        "requires_bilingual": False,
        "has_indigenous_set_aside": False,
        "nwpta_member": False,
    },
    {
        "code": "PEI",
        "name": "Prince Edward Island",
        "name_fr": "Île-du-Prince-Édouard",
        "jtype": "province",
        "trade_agreements": ["CFTA"],
        "procurement_portal_url": "https://www.gov.pe.ca/tenders/",
        "legislation_name": "Public Purchasing Act (RSPEI 1988, c. P-40)",
        "legislation_url": "https://www.princeedwardisland.ca/sites/default/files/legislation/P-40-Public%20Purchasing%20Act.pdf",
        "requires_bilingual": False,
        "has_indigenous_set_aside": False,
        "nwpta_member": False,
    },
    {
        "code": "NL",
        "name": "Newfoundland and Labrador",
        "name_fr": "Terre-Neuve-et-Labrador",
        "jtype": "province",
        "trade_agreements": ["CFTA"],
        "procurement_portal_url": "https://www.gov.nl.ca/tenders/",
        "legislation_name": "Public Procurement Act (SNL 2016, c. P-44.002)",
        "legislation_url": "https://assembly.nl.ca/legislation/sr/statutes/p44-002.htm",
        "requires_bilingual": False,
        "has_indigenous_set_aside": False,
        "nwpta_member": False,
    },
    {
        "code": "YT",
        "name": "Yukon",
        "name_fr": "Yukon",
        "jtype": "territory",
        "trade_agreements": ["CFTA"],
        "procurement_portal_url": "https://www.gov.yk.ca/tenders.html",
        "legislation_name": "Government Contracts Regulations (O.I.C. 1990/014)",
        "legislation_url": "https://legislation.yukon.ca/regulations/rw_2020-0010.pdf",
        "requires_bilingual": False,
        "has_indigenous_set_aside": True,  # Yukon First Nations Final Agreements set-aside provisions
        "nwpta_member": False,
    },
    {
        "code": "NWT",
        "name": "Northwest Territories",
        "name_fr": "Territoires du Nord-Ouest",
        "jtype": "territory",
        "trade_agreements": ["CFTA"],
        "procurement_portal_url": "https://www.iti.gov.nt.ca/en/services/procurement",
        "legislation_name": "Financial Administration Act (RSNWT 1988, c. F-4) / Business Incentive Policy",
        "legislation_url": "https://www.justice.gov.nt.ca/en/files/legislation/financial-administration/financial-administration.a.pdf",
        "requires_bilingual": False,
        "has_indigenous_set_aside": True,  # Business Incentive Policy (BIP) for NWT residents/businesses
        "nwpta_member": False,
    },
    {
        "code": "NU",
        "name": "Nunavut",
        "name_fr": "Nunavut",
        "jtype": "territory",
        "trade_agreements": ["CFTA"],
        "procurement_portal_url": "https://www.gov.nu.ca/finance/information/contracting-and-procurement",
        "legislation_name": "Financial Administration Act (RSNWT 1988, c. F-4, as duplicated for Nunavut) / NNI Policy",
        "legislation_url": "https://www.gov.nu.ca/sites/default/files/nni_policy_and_procedures_2020.pdf",
        "requires_bilingual": False,
        "has_indigenous_set_aside": True,  # NNI Policy (Nunavummi Nangminiqaqtunik Ikajuuti) — Inuit employment/business preference
        "nwpta_member": False,
    },
]


# ---------------------------------------------------------------------------
# PROCUREMENT FRAMEWORKS
# Thresholds are in CAD. None = not applicable / not party to that agreement.
# CFTA thresholds are 2024 indexed values (re-indexed every two years).
# CUSMA (formerly NAFTA) and CETA thresholds apply to the federal government only
# and are expressed in CAD at current exchange rates per Treasury Board guidance.
# ---------------------------------------------------------------------------

PROCUREMENT_FRAMEWORKS = [
    {
        "jurisdiction_code": "FED",
        "framework_name": "Government of Canada Procurement Framework",
        "legislation_ref": "Financial Administration Act (RSC 1985, c. F-11); Government Contracts Regulations (SOR/87-402)",
        "policy_ref": "Treasury Board Contracting Policy; PSPC Supply Manual",
        # Competitive thresholds — below these, directed / sole source permissible without formal competition
        "threshold_goods_cad": 25000.0,
        "threshold_services_cad": 40000.0,
        "threshold_construction_cad": 100000.0,
        # CFTA (Canadian Free Trade Agreement) — indexed thresholds 2024
        "cfta_goods_threshold": 33900.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        # CUSMA (Canada-United States-Mexico Agreement) Chapter 13 — 2024 CAD equivalents
        "cusma_goods_threshold": 99700.0,
        "cusma_services_threshold": 121200.0,
        # CETA (Comprehensive Economic and Trade Agreement) — 2024 CAD equivalents
        "ceta_goods_threshold": 236700.0,
        "ceta_services_threshold": 236700.0,
        # Construction thresholds under CUSMA/CETA
        "cusma_construction_threshold": 13500000.0,
        "ceta_construction_threshold": 9900000.0,
        "allowed_procurement_methods": [
            "RFP",           # Request for Proposal
            "RFQ",           # Request for Quotation
            "ITT",           # Invitation to Tender
            "RFSO",          # Request for Supply Arrangement
            "NPP",           # Non-competitive / Negotiated Procurement Process
            "LSA",           # Limited Solicitation Arrangement
            "SOLE_SOURCE",   # Non-competitive justification
            "COMPETITIVE_DIALOGUE",  # Innovation procurement
            "NUNAVUT_SET_ASIDE",     # Under NNI Policy (for fed contracts in Nunavut)
        ],
        "sole_source_grounds": [
            "NATIONAL_SECURITY",        # FAA s.40 / GCR s.6(a)
            "EMERGENCY",                # GCR s.6(b) — pressing emergency
            "SINGLE_SOURCE_SUPPLIER",   # GCR s.6(c) — only one supplier capable
            "INTEROPERABILITY",         # CFTA Art. 513(1)(d) — compatibility with existing equipment
            "PROTOTYPE",                # CFTA Art. 513(1)(e) — original development
            "ART_MUSEUM",               # Works of art / museum acquisitions
            "PUBLIC_INTEREST",          # Compelling public interest
            "FOLLOW_ON_CONTRACT",       # Consistent with original competition
            "INTELLECTUAL_PROPERTY",    # IP protection requires specific supplier
        ],
        "mandatory_clauses": [
            "Integrity Regime compliance (PSPC Ineligibility and Suspension Policy)",
            "Federal Contractors Program (FCP) — employment equity for contracts $1M+",
            "Accessibility requirements (ACA 2019)",
            "Official Languages Act compliance",
            "Privacy Act and ATIP obligations",
            "Canadian Content (where applicable — e.g., defence)",
            "Procurement Strategy for Indigenous Business (PSIB) set-aside eligibility check",
            "GreenProcure / greening government directive (where applicable)",
        ],
        "notes": (
            "Federal procurement is governed by PSPC (Public Services and Procurement Canada) and TBS "
            "(Treasury Board Secretariat). The Buyandsell.gc.ca portal (now CanadaBuys) is the primary "
            "procurement portal. CFTA thresholds are re-indexed every two years; CUSMA/CETA annually. "
            "The PSIB mandates minimum 5% of federal contracts by value to Indigenous businesses by 2025. "
            "Security clearances (PROTECTED/SECRET/TOP SECRET) are required for many federal IT contracts "
            "per the Policy on Government Security."
        ),
    },
    {
        "jurisdiction_code": "ON",
        "framework_name": "Ontario BPS Procurement Directive",
        "legislation_ref": "Ontario Procurement Act, 2019 (SO 2019, c. 7, Sched. 10)",
        "policy_ref": "BPS Procurement Directive (2023); Management Board of Cabinet Directives",
        "threshold_goods_cad": 100000.0,
        "threshold_services_cad": 100000.0,
        "threshold_construction_cad": 100000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "RFSO",
            "SOLE_SOURCE",
            "VENDOR_OF_RECORD",  # VOR — Ontario-specific standing offer arrangement
            "REVERSE_AUCTION",
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "PROTOTYPE",
            "NATIONAL_SECURITY",
            "FOLLOW_ON_CONTRACT",
            "PUBLIC_INTEREST",
        ],
        "mandatory_clauses": [
            "Accessibility for Ontarians with Disabilities Act (AODA) compliance",
            "Ontario Public Service Procurement Ethical Standard",
            "French Language Services Act compliance (where services offered in French)",
            "Vendor Performance Program reporting",
            "Broader Public Sector accountability requirements",
        ],
        "notes": (
            "The BPS Procurement Directive applies to hospitals, universities, colleges, and school boards "
            "receiving provincial funding, as well as OPS ministries. VOR (Vendor of Record) arrangements "
            "are widely used for IT and professional services. AODA/WCAG 2.1 AA compliance is mandatory "
            "for all publicly accessible digital deliverables. Ontario is not a NWPTA member."
        ),
    },
    {
        "jurisdiction_code": "BC",
        "framework_name": "BC Procurement Services Act Framework",
        "legislation_ref": "Procurement Services Act (SBC 2003, c. 22)",
        "policy_ref": "BC Procurement Policy and Procedures; Core Policy and Procedures Manual Ch. 6",
        "threshold_goods_cad": 75000.0,
        "threshold_services_cad": 75000.0,
        "threshold_construction_cad": 200000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "RFSO",
            "SOLE_SOURCE",
            "SHORT_LISTING",     # Two-stage RFP
            "DIRECT_AWARD",      # Under standing offer
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "PROTOTYPE",
            "NATIONAL_SECURITY",
            "FOLLOW_ON_CONTRACT",
            "INDIGENOUS_SET_ASIDE",  # First Nations procurement set-asides
        ],
        "mandatory_clauses": [
            "BC Accessibility Act compliance",
            "Privacy protection per Freedom of Information and Protection of Privacy Act (FOIPPA)",
            "BC Data Residency requirements for sensitive data",
            "Living Wage policy (select contracts)",
            "First Nations consultation obligations",
            "Carbon neutral operations clause (where applicable)",
        ],
        "notes": (
            "BC is a NWPTA member (with AB and SK). BCBid is the primary portal. "
            "BC requires data residency within Canada for personal information under FOIPPA. "
            "The Province has established Indigenous procurement targets and a First Nations Technology "
            "Council partnership for IT procurement. Standing offer agreements (SOAs) through Shared "
            "Services BC are commonly used for commodity IT purchases."
        ),
    },
    {
        "jurisdiction_code": "AB",
        "framework_name": "Alberta Purchasing Connection Framework",
        "legislation_ref": "Government Organization Act (RSA 2000, c. G-10); Financial Administration Act",
        "policy_ref": "Alberta Purchasing Connection (APC) Policy; Supply Chain Management Directive",
        "threshold_goods_cad": 75000.0,
        "threshold_services_cad": 75000.0,
        "threshold_construction_cad": 200000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "RFSO",
            "SOLE_SOURCE",
            "DIRECT_AWARD",
            "COOPERATIVE_PURCHASING",  # Allowed via existing provincial arrangements
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "PROTOTYPE",
            "NATIONAL_SECURITY",
            "FOLLOW_ON_CONTRACT",
            "PUBLIC_INTEREST",
        ],
        "mandatory_clauses": [
            "Freedom of Information and Protection of Privacy Act (FOIPP) compliance",
            "Alberta Labour Relations Code provisions (construction)",
            "Environmental protection clauses per EPEA",
            "Employment equity considerations",
        ],
        "notes": (
            "Alberta uses Merx/MERX as its primary procurement portal (Alberta Purchasing Connection). "
            "Alberta is a NWPTA member. No provincial sales tax simplifies procurement cost calculations. "
            "Health procurement is managed separately by Alberta Health Services (AHS), one of the largest "
            "health procurement entities in Canada."
        ),
    },
    {
        "jurisdiction_code": "QC",
        "framework_name": "Quebec ARPCB / SEAO Framework",
        "legislation_ref": (
            "Act Respecting Contracts of Public Bodies (CQLR c. C-65.1); "
            "Charter of the French Language (CQLR c. C-11)"
        ),
        "policy_ref": "Conseil du trésor Politique de gestion contractuelle; Directives du secrétariat",
        "threshold_goods_cad": 104100.0,   # 2024 ARPCB threshold (indexed)
        "threshold_services_cad": 104100.0,
        "threshold_construction_cad": 270300.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "AO",            # Appel d'offres (open tender)
            "AOR",           # Appel d'offres sur invitation (invitation to tender)
            "GREA",          # Gré à gré / sole source
            "ACCORD_CADRE",  # Framework agreement
            "PROCESSUS_SELECTIF",  # Selective process
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "PROTOTYPE",
            "PUBLIC_INTEREST",
            "ARTS_CULTURAL",  # Specific to QC for artistic/cultural contracts
            "FOLLOW_ON_CONTRACT",
        ],
        "mandatory_clauses": [
            "Charter of the French Language compliance — all contract documents in French",
            "Act Respecting Contracts of Public Bodies integrity requirements (Regie du batiment)",
            "Autorité des marchés publics (AMP) oversight compliance",
            "SEAO publication requirement",
            "Attestation de Revenu Québec (tax compliance certificate) for contracts $25K+",
            "Systeme electronique d'appel d'offres (SEAO) mandatory posting",
        ],
        "notes": (
            "Quebec requires all procurement documents to be in French per the Charter of the French Language. "
            "The Autorité des marchés publics (AMP) provides independent oversight of public procurement. "
            "SEAO (Système électronique d'appel d'offres) is the mandatory tender publication system. "
            "Integrity requirements are strict — suppliers must obtain authorization from the AMF or "
            "Régie du bâtiment for contracts above thresholds. Quebec is not a NWPTA member. "
            "Construction thresholds are governed by the Act respecting labour relations in the construction industry."
        ),
    },
    {
        "jurisdiction_code": "SK",
        "framework_name": "Saskatchewan Purchasing Connection Framework",
        "legislation_ref": "Government Administration Act (SS 2014, c. G-5.01)",
        "policy_ref": "Saskatchewan Procurement Policy; Crown Investments Corporation procurement rules",
        "threshold_goods_cad": 50000.0,
        "threshold_services_cad": 50000.0,
        "threshold_construction_cad": 100000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "SOLE_SOURCE",
            "DIRECT_AWARD",
            "STANDING_OFFER",
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "FOLLOW_ON_CONTRACT",
            "PUBLIC_INTEREST",
        ],
        "mandatory_clauses": [
            "Freedom of Information and Protection of Privacy Act (FOIP) compliance",
            "Saskatchewan Human Rights Code compliance",
            "First Nations and Métis procurement considerations",
        ],
        "notes": (
            "Saskatchewan is a NWPTA member. The Saskatchewan Purchasing Connection (SPC) portal lists "
            "all competitive opportunities. CIC (Crown Investments Corporation) subsidiaries such as "
            "SaskTel and SaskPower have their own procurement policies derived from provincial framework."
        ),
    },
    {
        "jurisdiction_code": "MB",
        "framework_name": "Manitoba Materials Management Framework",
        "legislation_ref": "The Financial Administration Act (CCSM c. F55); The Purchasing Act (CCSM c. P187)",
        "policy_ref": "Materials Management Policy (2022); Treasury Board Secretariat directives",
        "threshold_goods_cad": 50000.0,
        "threshold_services_cad": 50000.0,
        "threshold_construction_cad": 100000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "SOLE_SOURCE",
            "STANDING_OFFER",
            "DIRECT_AWARD",
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "FOLLOW_ON_CONTRACT",
            "PUBLIC_INTEREST",
        ],
        "mandatory_clauses": [
            "The Freedom of Information and Protection of Privacy Act (FIPPA) compliance",
            "The Human Rights Code (Manitoba) compliance",
            "Province of Manitoba Pay Equity requirements",
        ],
        "notes": (
            "Manitoba is NOT a NWPTA member — a key distinction from the western provinces of BC, AB, and SK. "
            "Manitoba participates in CFTA. The province uses its own tendering portal. "
            "Crown corporations (Manitoba Hydro, Manitoba Public Insurance) have separate procurement policies."
        ),
    },
    {
        "jurisdiction_code": "NB",
        "framework_name": "New Brunswick Procurement Act Framework",
        "legislation_ref": "Procurement Act (SNB 2012, c. 12)",
        "policy_ref": "New Brunswick Procurement Policy; Service New Brunswick procurement guidelines",
        "threshold_goods_cad": 25000.0,
        "threshold_services_cad": 50000.0,
        "threshold_construction_cad": 100000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "SOLE_SOURCE",
            "STANDING_OFFER",
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "FOLLOW_ON_CONTRACT",
            "PUBLIC_INTEREST",
        ],
        "mandatory_clauses": [
            "Official Languages Act (NB) — bilingual contract documents required",
            "Right to Information and Protection of Privacy Act (RTIPPA) compliance",
            "New Brunswick Human Rights Act compliance",
            "Service New Brunswick (SNB) IT procurement coordination for government IT",
        ],
        "notes": (
            "New Brunswick is Canada's only officially bilingual province; all procurement documents "
            "must be available in both English and French. Service New Brunswick (SNB) centralizes "
            "IT and shared services procurement. NB Tenders is the public portal. "
            "The Procurement Act introduced standardized processes replacing the previous Public "
            "Purchasing Act and aligned NB with CFTA obligations."
        ),
    },
    {
        "jurisdiction_code": "NS",
        "framework_name": "Nova Scotia Procurement Act Framework",
        "legislation_ref": "Nova Scotia Procurement Act (SNS 2011, c. 12)",
        "policy_ref": "Nova Scotia Procurement Policy and Guidelines; Internal Services procurement directives",
        "threshold_goods_cad": 25000.0,
        "threshold_services_cad": 50000.0,
        "threshold_construction_cad": 100000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "SOLE_SOURCE",
            "STANDING_OFFER",
            "DIRECT_AWARD",
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "FOLLOW_ON_CONTRACT",
            "PUBLIC_INTEREST",
        ],
        "mandatory_clauses": [
            "Freedom of Information and Protection of Privacy Act (FOIPOP) compliance",
            "Nova Scotia Human Rights Act compliance",
            "Nova Scotia Accessibility Act compliance (2017)",
        ],
        "notes": (
            "Nova Scotia centralized much of its IT procurement under the Department of Internal Services. "
            "The province has introduced social procurement considerations, including Mi'kmaw procurement "
            "provisions under treaty obligations. All tenders posted on novascotia.ca/tenders."
        ),
    },
    {
        "jurisdiction_code": "PEI",
        "framework_name": "PEI Public Purchasing Act Framework",
        "legislation_ref": "Public Purchasing Act (RSPEI 1988, c. P-40)",
        "policy_ref": "PEI Procurement Policy; Treasury Board directives",
        "threshold_goods_cad": 25000.0,
        "threshold_services_cad": 25000.0,
        "threshold_construction_cad": 50000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "SOLE_SOURCE",
            "DIRECT_AWARD",
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "FOLLOW_ON_CONTRACT",
            "PUBLIC_INTEREST",
        ],
        "mandatory_clauses": [
            "Freedom of Information and Protection of Privacy Act (FOIPP) compliance",
            "PEI Human Rights Act compliance",
        ],
        "notes": (
            "Prince Edward Island is the smallest province by population and often leverages cooperative "
            "purchasing arrangements with other Atlantic provinces and the federal government to achieve "
            "economies of scale. The Public Purchasing Act is one of Canada's older procurement statutes "
            "and is overdue for modernization. PEI participates in CFTA."
        ),
    },
    {
        "jurisdiction_code": "NL",
        "framework_name": "Newfoundland and Labrador Public Procurement Agency Framework",
        "legislation_ref": "Public Procurement Act (SNL 2016, c. P-44.002)",
        "policy_ref": "NL Public Procurement Agency (PPA) Policy and Directives",
        "threshold_goods_cad": 25000.0,
        "threshold_services_cad": 50000.0,
        "threshold_construction_cad": 100000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "SOLE_SOURCE",
            "STANDING_OFFER",
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "FOLLOW_ON_CONTRACT",
            "PUBLIC_INTEREST",
            "MUSKRAT_FALLS_RELATED",  # Historical note — large infrastructure project exceptions
        ],
        "mandatory_clauses": [
            "Access to Information and Protection of Privacy Act (ATIPPA) compliance",
            "NL Human Rights Act compliance",
            "Local content — NL suppliers given preference for lower-value procurements (Industrial Benefits Policy)",
        ],
        "notes": (
            "The Public Procurement Agency (PPA) was established in 2016 to centralize and professionalize "
            "procurement. NL has an Industrial Benefits Policy encouraging local supplier engagement. "
            "The province has significant resource sector procurement (offshore oil and gas). "
            "Atlantic Procurement Agreement facilitates cross-provincial cooperation with NS, NB, and PEI."
        ),
    },
    {
        "jurisdiction_code": "YT",
        "framework_name": "Yukon Government Contracts Regulations Framework",
        "legislation_ref": "Government Contracts Regulations (O.I.C. 1990/014); Financial Administration Act (RSY 2002, c. 87)",
        "policy_ref": "Yukon Government Procurement Policy; First Nations Contracting preference",
        "threshold_goods_cad": 25000.0,
        "threshold_services_cad": 25000.0,
        "threshold_construction_cad": 100000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "SOLE_SOURCE",
            "DIRECT_AWARD",
            "FIRST_NATIONS_SOLE_SOURCE",  # Under Final Agreement provisions
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "FOLLOW_ON_CONTRACT",
            "PUBLIC_INTEREST",
            "FIRST_NATIONS_FINAL_AGREEMENT",  # Specific to Yukon First Nations Final Agreements
        ],
        "mandatory_clauses": [
            "Access to Information and Protection of Privacy Act (ATIPP) compliance",
            "Yukon Human Rights Act compliance",
            "First Nations Final Agreement socio-economic provisions",
            "Contracting preference for Yukon businesses (threshold-based)",
        ],
        "notes": (
            "Yukon has 11 self-governing First Nations with Final Agreements that include procurement "
            "obligations for the territorial government. The Government of Yukon must consult with and "
            "give preference to Yukon businesses and First Nations businesses. "
            "Yukon participates in CFTA but is a small jurisdiction with limited procurement volume."
        ),
    },
    {
        "jurisdiction_code": "NWT",
        "framework_name": "GNWT Procurement / Business Incentive Policy Framework",
        "legislation_ref": "Financial Administration Act (RSNWT 1988, c. F-4); Contracting Regulations",
        "policy_ref": "GNWT Business Incentive Policy (BIP); Procurement and Risk Management Policy",
        "threshold_goods_cad": 25000.0,
        "threshold_services_cad": 25000.0,
        "threshold_construction_cad": 100000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "SOLE_SOURCE",
            "BIP_DIRECTED",   # Business Incentive Policy directed award to NWT businesses
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "INTEROPERABILITY",
            "FOLLOW_ON_CONTRACT",
            "PUBLIC_INTEREST",
            "BIP_QUALIFYING_BUSINESS",  # NWT Business Incentive Policy qualification
        ],
        "mandatory_clauses": [
            "Access to Information and Protection of Privacy Act (ATIPP) compliance",
            "NWT Human Rights Act compliance",
            "Business Incentive Policy (BIP) — mandatory NWT business preference points in evaluation",
            "NWT Negotiated Contracts Policy for Aboriginal businesses",
        ],
        "notes": (
            "The Business Incentive Policy (BIP) is a cornerstone of GNWT procurement, requiring "
            "evaluation criteria that give preference to NWT-based businesses. The policy includes "
            "additional preference for businesses owned or employing Northwest Territories Aboriginal peoples. "
            "The Negotiated Contracts Policy allows sole-source awards to qualifying Aboriginal "
            "businesses without tender for contracts up to specified thresholds. GNWT participates in CFTA."
        ),
    },
    {
        "jurisdiction_code": "NU",
        "framework_name": "Government of Nunavut NNI Policy Framework",
        "legislation_ref": "Financial Administration Act (RSNWT 1988, c. F-4, as duplicated for Nunavut); Contracting Regulations",
        "policy_ref": "NNI Policy (Nunavummi Nangminiqaqtunik Ikajuuti) 2020; GN Procurement and Contracting Policy",
        "threshold_goods_cad": 25000.0,
        "threshold_services_cad": 25000.0,
        "threshold_construction_cad": 100000.0,
        "cfta_goods_threshold": 121200.0,
        "cfta_services_threshold": 121200.0,
        "cfta_construction_threshold": 9900000.0,
        "cusma_goods_threshold": None,
        "cusma_services_threshold": None,
        "ceta_goods_threshold": None,
        "ceta_services_threshold": None,
        "cusma_construction_threshold": None,
        "ceta_construction_threshold": None,
        "allowed_procurement_methods": [
            "RFP",
            "RFQ",
            "ITT",
            "SOLE_SOURCE",
            "NNI_DIRECTED",        # NNI sole-source to Inuit firm
            "NEGOTIATED_CONTRACT", # With Inuit organizations per Nunavut Agreement
        ],
        "sole_source_grounds": [
            "EMERGENCY",
            "SINGLE_SOURCE_SUPPLIER",
            "FOLLOW_ON_CONTRACT",
            "PUBLIC_INTEREST",
            "NNI_INUIT_BUSINESS",       # NNI Policy preference for Inuit-owned businesses
            "NUNAVUT_LAND_CLAIMS_AGREEMENT",  # Article 24 — Inuit employment & business obligations
        ],
        "mandatory_clauses": [
            "Access to Information and Protection of Privacy Act (ATIPP) compliance",
            "NNI Policy compliance — mandatory Inuit employment benefit plans (IEBPs) for large contracts",
            "Nunavut Land Claims Agreement (NLCA) Article 24 obligations",
            "Bilingual (English/Inuktitut) communication requirements for contract administration",
            "Inuit Firm preference evaluation criteria",
        ],
        "notes": (
            "The NNI Policy (Nunavummi Nangminiqaqtunik Ikajuuti — 'Support from Nunavummiut') is the "
            "Government of Nunavut's procurement preference framework. It requires that Inuit firms and "
            "businesses employing Nunavut Inuit receive preference in all government procurement. "
            "Large contracts require Inuit Employment Benefit Plans (IEBPs). The Nunavut Land Claims "
            "Agreement (Article 24) mandates Inuit employment in government and government-funded contracts. "
            "Nunavut participates in CFTA with carve-outs protecting NNI policy preferences. "
            "Remote delivery costs and logistics are significant procurement considerations."
        ),
    },
]
