# Lexara — Procurement & Contract Roles: Needs, Requirements, Feature Map & Build Gaps

_Status: Discovery / product-strategy document. Author: product. Date: 2026-06-04._
_Scope: Map the four operating roles (Strategic Sourcing Advisor, Procurement Officer, Contracts Manager, in-house Procurement/Contracts Lawyer) plus the general legal professional, define their responsibilities and obligations, derive system requirements, map those to Lexara's current capabilities, identify build gaps, and list the knowledge sources required to build._

---

## 0. How to read this document

The procurement-to-contract lifecycle is a **relay**: each role's output is the next role's input. Lexara's strategic opportunity is to be the connective tissue across that relay — one system where the sourcing strategy, the bidding documents, the awarded contract, and the obligation register all share the same clause intelligence and audit trail.

```
 Business need
     │
     ▼
[1] Strategic Sourcing Advisor ──(sourcing strategy + market research)──►
[2] Procurement Officer ─────────(RFP/RFT/RFQ/RFSQ + evaluation + award)──►
[3] Contracts Manager ───────────(obligation register + performance + renewal)──►
                                  ▲                         ▲
[5] Procurement / Contracts Lawyer (retainer) ── legal review/redline/risk across ALL phases
[4] Vendor / Supplier Management ── runs in parallel across [1]→[3]
```

**Positioning principle (from the brief):** Lexara is built **for non-legal professionals first** — sourcing advisors, procurement officers, contract managers who must produce legally sound documents without a lawyer in the room — **and is simultaneously a force-multiplier for lawyers**, compressing drafting and review time. Every feature must therefore have two faces: a *guided, plain-language* mode for the non-lawyer and a *power/redline* mode for the lawyer.

---

## 1. Lifecycle backbone (the spine all roles hang off)

| Phase | Phase name | Primary role | Key artifacts |
|---|---|---|---|
| P0 | Intake & requirement definition | SSA (with stakeholder) | Statement of need, business case, specification/SOW draft |
| P1 | Market research & strategy | SSA | Market/supply-market analysis, should-cost model, supplier long/short list, **procurement method recommendation** |
| P2 | Solicitation drafting | Procurement Officer | RFI, RFP, RFT/ITT, RFQ, RFSQ/RFSO/RFSA, EOI; evaluation framework; T&Cs |
| P3 | Bidding / tender management | Procurement Officer | Postings, Q&A & addenda, bid receipt, compliance screen |
| P4 | Evaluation & award | Procurement Officer (+ Lawyer) | Scoring matrices, evaluation report, award recommendation, debrief, standstill |
| P5 | Contract formation & kickoff | Procurement Officer → Contracts Manager | Executed contract, schedules, kickoff package |
| P6 | Contract administration | Contracts Manager | Obligation register, milestone/SLA tracker, change/variation log |
| P7 | Performance & vendor mgmt | Contracts Manager + Vendor Mgmt | Scorecards, KPI dashboards, risk/insurance currency |
| P8 | Renewal / variation / closeout | Contracts Manager (+ Lawyer) | Renewal calendar, amendments, closeout & lessons-learned |
| X | Legal assurance | Lawyer (retainer) | Redlines, risk memos, fallback playbooks, dispute support — spans P2–P8 |

This spine is the data model Lexara should converge on: a **Matter/Engagement** object that threads requirement → solicitation → bid → contract → obligations, so nothing is re-keyed between roles.

---

## 2. Role deep-dives — responsibilities, obligations, decisions, pain points

Each role is a generalist across **all commodities and sectors** — goods, services, construction, IT/digital, professional services, healthcare, defence, energy/utilities, transportation, infrastructure — and across **both public and private** procurement. That breadth is a hard requirement: the same officer drafts an IT SaaS RFP one week and a construction RFT the next. Lexara must carry sector/commodity context (templates, standard forms, risk norms) rather than assume one vertical.

### 2.1 Strategic Sourcing Advisor (SSA)

**Mission.** Translate a business requirement into a *feasible and executable* sourcing strategy — deciding **what** to buy, **how** to go to market, and **from which supply base**, before any document is drafted.

**Core responsibilities**
- Challenge and clarify requirements (need vs. want; outcome vs. specification; make-vs-buy).
- Spend & demand analysis; category management and category strategy.
- **Market research / supply-market intelligence:** supplier landscape (long-list → short-list), market structure & competitiveness (concentration, switching costs, Porter's Five Forces), price/cost trends, capacity, lead times, supply risk, ESG/diversity availability.
- Should-cost / cost modelling; total cost of ownership (TCO); savings and value targets.
- **Procurement method / route-to-market selection:** open competitive tender, selective/invited, prequalified pool, standing offer/supply arrangement, framework, sole/single-source justification, e-auction, unsolicited proposal.
- Risk assessment of the strategy (supply, delivery, reputational, compliance).
- Public-sector overlay: trade-agreement thresholds & obligations (CFTA, CETA, CPTPP, WTO-GPA), non-discrimination, jurisdictional set-asides (e.g., Indigenous procurement).

**Obligations / accountabilities.** Defensible, evidence-based strategy; value-for-money; compliance with policy and trade agreements; documented method justification (especially for any non-competitive route).

**Key decisions.** Competitive vs. non-competitive; single vs. multi-source; method (RFP vs. RFT vs. RFQ vs. RFSQ); evaluation philosophy (lowest-price-compliant vs. best-value); bundling/lotting.

**Pain points Lexara can attack.** Market research is slow and manual; method selection is tribal knowledge; business cases are written from scratch; thresholds/trade-agreement rules are easy to get wrong.

**Outputs (Lexara should generate/assist).** Market research brief, supplier long/short-list, should-cost summary, **procurement method recommendation with rationale**, sourcing strategy & business case.

### 2.2 Procurement Officer (PO)

**Mission.** Convert the SSA's strategy into **compliant, defensible bidding documents** and run the competition through to award and contract kickoff.

**Core responsibilities**
- **Draft the solicitation** appropriate to the method:
  - **RFI** — Request for Information (market sounding; non-binding).
  - **RFP** — Request for Proposal (best-value; qualitative + price, weighted/rated criteria).
  - **RFT / ITT** — Request for Tender / Invitation to Tender (compliance + price; common in construction/goods; binding bid).
  - **RFQ** — Request for Quotation (defined spec, price-driven; commodities/low-complexity).
  - **RFSQ** — Request for Supplier Qualification / prequalification (build a qualified pool / vendor of record).
  - **RFSO / RFSA** — Request for Standing Offer / Supply Arrangement; **EOI** — Expression of Interest.
- Build the **evaluation framework:** mandatory/pass-fail criteria, rated/technical criteria & weights, pricing/financial evaluation method, scoring scales, consensus process.
- Assemble terms & conditions, instructions to bidders, SOW/specifications, submission requirements, mandatory forms.
- Manage the **workflow to kickoff:** approvals, posting to portals (CanadaBuys/MERX/bids&tenders/Biddingo, or private e-sourcing), bidder Q&A and **addenda**, bid receipt/closing, compliance screening, evaluation coordination, award recommendation, notifications, **debrief**, standstill, and contract execution → kickoff handover.

**Obligations / accountabilities (high-stakes, especially public).**
- **Fair, open, transparent, competitive** process; equal treatment of bidders.
- Canadian "**Contract A / Contract B**" doctrine (*R. v. Ron Engineering*): issuing a compliant tender can create a binding bid contract — duty of fairness, no undisclosed criteria, no bid shopping.
- Adherence to trade agreements, procurement directives/policy, and audit requirements; complete, defensible evaluation record (bid-protest / CITT exposure).

**Key decisions.** Mandatory vs. rated weighting; price/technical split; compliance determinations; addendum vs. cancel-and-reissue; award and debrief handling.

**Pain points Lexara can attack.** Drafting RFx from inconsistent templates; misaligned/ambiguous evaluation criteria; clause drift and non-compliant T&Cs; tracking addenda; building defensible scoring records.

**Outputs (Lexara should generate/assist).** Full RFx document set, evaluation matrix & scoring workbook, Q&A/addendum drafts, compliance checklist, evaluation report & award recommendation, debrief letter.

### 2.3 Contracts Manager (CM)

**Mission.** Take the awarded contract as input and **manage obligations and performance** across the live contract until closeout — protecting value, managing change and risk, and ensuring both parties meet their commitments.

**Core responsibilities (Contract Lifecycle Management — CLM, post-award)**
- **Obligation management:** extract and track *both buyer- and supplier-side* obligations, deliverables, milestones, service levels.
- **Key-date management:** term, expiry, **renewal/option windows, notice periods, auto-renew triggers**.
- **Performance management:** SLA/KPI monitoring, deliverable acceptance, vendor scorecards, performance reporting.
- **Change & variation management:** change orders, scope creep control, price/schedule adjustments, amendments.
- **Risk & compliance:** insurance/bond/WSIB currency, certifications, indemnity/liability triggers, force-majeure, data-protection (PIPEDA) commitments.
- **Financial:** invoice verification against milestones/rates, holdbacks, payment terms, savings realization.
- **Disputes/claims, remedies, termination management; closeout & lessons-learned; contract repository & audit trail.**

**Obligations / accountabilities.** Ensure delivery of contracted value; enforce/honour obligations; maintain a complete, auditable record; protect against missed renewals, unmanaged scope creep, and lapsed compliance.

**Key decisions.** Accept/reject deliverables; approve variations; exercise renewal/termination; escalate disputes; release holdback.

**Pain points Lexara can attack.** Obligations buried in PDFs and never tracked; missed renewal/notice dates; manual SLA monitoring; no single obligation register; reconstructing the audit trail after the fact.

**Outputs (Lexara should generate/assist).** Obligation register, milestone & SLA tracker, renewal/notice calendar with alerts, variation log, vendor scorecard, closeout report.

### 2.4 Vendor / Supplier Management (cross-cutting)

Often split across SSA (pre-award) and CM (post-award), sometimes a dedicated SRM function.

**Responsibilities.** Supplier master data; supplier segmentation (strategic/leverage/bottleneck/routine — Kraljic); qualification & onboarding; performance & risk monitoring; relationship governance (QBRs); supplier development; ESG/diversity/compliance tracking; consolidated spend-by-supplier view.

**Outputs (Lexara should assist).** Supplier profile/master record, segmentation view, performance & risk scorecard, qualification status, consolidated supplier spend & contract footprint.

### 2.5 Procurement / Contracts Lawyer — in-house, on retainer (Role 5)

**Mission.** Provide **legal assurance across the whole lifecycle** — drafting/redlining, risk identification and mitigation, compliance, negotiation support, and dispute handling — for a private or public organization. The brief explicitly wants Lexara to **speed up the lawyer's drafting and review**.

**Core responsibilities**
- Draft / review / **redline** contracts, schedules, T&Cs; maintain precedent and **clause libraries / playbooks** (preferred + fallback positions).
- Legal risk assessment: limitation of liability, indemnity, IP/licensing, **data privacy (PIPEDA)**, confidentiality, warranties, termination, governing law, dispute resolution, insurance.
- Procurement-law compliance (public): trade agreements, fairness/Contract A, conflict of interest, bid-protest/CITT readiness; (private): commercial/contract law, corporate policy.
- Negotiation support; positions and fallbacks; sign-off and escalation.
- Dispute, claims, and litigation support; regulatory/jurisdictional currency (Ontario law / federal where applicable).

**Obligations / accountabilities.** Sound legal advice; risk within appetite; regulatory compliance; privilege and confidentiality; defensible records.

**Key decisions.** Acceptable vs. unacceptable risk; redline positions and fallbacks; escalate vs. accept; sign-off.

**Pain points Lexara can attack.** Repetitive first-pass review and redlining; clause-by-clause comparison against playbook/standard; spotting missing or off-market clauses; keeping precedent/clause libraries current; producing risk memos fast.

**What the lawyer needs from Lexara specifically.** Power-mode redlining with tracked changes; clause-library/playbook comparison ("does this deviate from our standard, and how?"); risk-scored review with citations to source/standard; export to Word with redlines; an explicit **"AI assistance, not legal advice"** boundary and auditability of every suggestion.

---

## 3. Consolidated requirements catalog (role-agnostic → role-tagged)

Derived from §2. **R# = requirement.** Roles: SSA, PO, CM, VM, LAW. Phase per §1.

| R# | Requirement | Roles | Phase |
|---|---|---|---|
| R01 | Requirement/need intake & structuring (turn a plain-language need into a structured spec/SOW skeleton) | SSA, PO | P0 |
| R02 | Market & supply-market research synthesis (supplier landscape, structure, price/risk) | SSA, VM | P1 |
| R03 | Should-cost / TCO modelling support | SSA | P1 |
| R04 | **Procurement method recommendation** (RFP/RFT/RFQ/RFSQ/standing offer/sole-source) with rationale & threshold/trade-agreement check | SSA | P1 |
| R05 | Supplier discovery / long-list → short-list | SSA, VM | P1 |
| R06 | **Solicitation drafting / generation** for each RFx type, sector-aware, from templates + clause library | PO, LAW | P2 |
| R07 | **Evaluation framework builder** (mandatory/rated criteria, weights, scoring scales, price method) | PO | P2 |
| R08 | T&C / clause assembly with compliance & consistency checks (Contract A safe, trade-agreement compliant) | PO, LAW | P2 |
| R09 | Q&A / addendum management & version control | PO | P3 |
| R10 | Bid compliance screening (mandatory checklist) | PO | P3/P4 |
| R11 | Evaluation & scoring workbook + consensus + defensible evaluation report | PO | P4 |
| R12 | Award recommendation + debrief letter generation | PO, LAW | P4 |
| R13 | Contract assembly from awarded bid + schedules; kickoff package | PO, CM | P5 |
| R14 | **Obligation extraction** (both parties) into an obligation register | CM, LAW | P6 |
| R15 | **Key-date / renewal / notice / auto-renew tracking + alerts** | CM | P6/P8 |
| R16 | Milestone / deliverable / SLA / KPI tracking & performance reporting | CM, VM | P7 |
| R17 | Change / variation / amendment management & log | CM, LAW | P6/P8 |
| R18 | Compliance currency tracking (insurance, bond, WSIB, certifications, privacy commitments) | CM, VM, LAW | P7 |
| R19 | Vendor master, segmentation, scorecards, risk monitoring | VM, CM, SSA | P1/P7 |
| R20 | Closeout, lessons-learned, renewal-vs-recompete decision support | CM, SSA | P8 |
| R21 | **Contract/clause review, risk scoring, redline** vs. playbook/standard | LAW, PO, CM | X |
| R22 | Clause library / playbook (preferred + fallback) management | LAW, PO | X |
| R23 | Missing-clause / off-market detection | LAW, PO, CM | X |
| R24 | Risk memo / summary generation with citations | LAW | X |
| R25 | Audit trail, versioning, defensibility, role-based access | ALL | ALL |
| R26 | Jurisdiction & sector context engine (ON/PIPEDA, federal SACC, CCDC for construction, IT MSAs, etc.) | ALL | ALL |
| R27 | Plain-language "guided" mode for non-lawyers + power/redline mode for lawyers; "not legal advice" boundary | ALL | ALL |

---

## 4. Lexara current capabilities (grounded in a live inventory of `app/`)

> **Important correction to first impressions.** Lexara is **not** a thin "analyze one contract" API. A full inventory of routers/services/models shows a **6-feature contract-intelligence platform with a deep Canadian-procurement knowledge layer already in place.** Much of the procurement/CLM relay is *already partially built*. The gap analysis below reflects that reality.

### 4.1 The six shipped product features

| # | Feature | Routers / services | Serves roles |
|---|---|---|---|
| F1 | **Portfolio Obligation Index** — contract & obligation CRUD + cross-contract **cascade detection** (deadline ripple, penalty overlap, liability-cap conflict) | `portfolio_routes`, `cascade_detector` | **CM**, VM |
| F2 | **SOW Workbench** — real-time AI **drafting guidance + section generation** for procurement documents; 11-section templates by commodity/jurisdiction/method; completeness scoring; rule-based constraint warnings (security clearance, bilingual, Indigenous set-aside, AODA); evaluation & SLA templates; export | `workbench_routes`, `workbench_service` | **PO**, **SSA**, LAW |
| F3 | **Obligation Matrix** — temporal dependency graph; extracts obligations; resolves relative deadlines ("30 business days after award") with **business-day + holiday math** and anchor resolution | `obligation_temporal_routes`, `obligation_extractor`, `obligation_resolver`, `nlp/temporal_extractor` | **CM** |
| F4 | **Dark Obligation Detector** — flags **missing standard clauses** by contract type via FAISS similarity + **peer-frequency** thresholds; CUAD (510-contract) corpus + 94/41 clause categories | `dark_obligation_routes`, `dark_obligation_service` | LAW, **CM**, **PO** |
| F5 | **Clause Negotiation Simulator** — multi-round **opposing-counsel AI**, BATNA scoring, concession ledger, cross-clause trading, government non-negotiables, jurisprudence linking, multi-party collaboration | `negotiation_routes`, `negotiation_ai`, `batna_engine`, `clause_weights`, `scenario_simulator` | LAW, **PO** |
| F6 | **Bid Stress-Test** — N-bid **obligation-matrix comparison** across multiple bids (Excel) | `bid_comparison_routes`, `compare_service` | **PO**, **CM** |

### 4.2 Core analysis + supporting services (LIVE)

- **5-mode contract analysis** (`contracts.py`): summary · risk-score (0–100 w/ category breakdown) · key-risks (severity/section/recommendation) · missing-clauses · clause-extraction + redline suggestions. (Serves **LAW** review and everyone.)
- **Plain-language linter** (`linter_service`): legalese, passive voice, gendered/vague language — **directly serves the non-lawyer audience** (R27).
- **Canadian citation validator** (`citation_service`): McGill Guide 10th ed. — statutes/regs/cases.
- **Upload** (`upload.py`): PDF/DOCX/TXT text extraction (no scanned-doc OCR yet).
- **Ingestion** (`ted_client`, `ocp_client`, `pipeline`, `learning`): TED + OCP/OCDS tenders → `Tender` rows → clause learning → FAISS.
- **LLM waterfall** Groq → HF/SaulLM → Claude Haiku; **`lexara_training_data.json`** = SACC/Ontario procurement-clause corpus + SaulLM fine-tune notebook.

### 4.3 The knowledge layer (this is the moat — already modeled)

`app/models/knowledge.py` + taxonomy models already encode:
- **`ProcurementFramework`** — per-jurisdiction legislation/policy refs, **goods/services/construction thresholds**, **CFTA/CUSMA/CETA thresholds**, **allowed_procurement_methods**, **sole_source_grounds**, **mandatory_clauses**.
- **`KnowledgeArticle`** — atomic clause/guidance/mandatory-req/SLA articles tagged by jurisdiction, commodity, procurement phase, **source (SACC / BPS_DIRECTIVE / CFTA / TB_POLICY)**, `is_mandatory`, `risk_if_omitted`, `applies_above_value_cad`; bilingual fields present.
- **`SOWTemplate` / `EvaluationTemplate` / `SLATemplate`** — section blueprints, weighted evaluation criteria, KPI sets.
- **`JurisprudenceArticle`** — Canadian **case law** indexed by clause type + jurisdiction (court, year, principle, citation).
- **`CommoditySector/Category/Subcategory`** taxonomy + **`Jurisdiction`** (ON/FED/provincial/municipal, trade agreements, bilingual flag, thresholds).
- Procurement-method enum already includes **RFP, RFQ, ITT (=RFT), RFSO, NPP, LSA, SOLE_SOURCE**.

**Net read:** Lexara already covers, at least partially, the **PO drafting** (F2), **CM obligation/CLM** (F1/F3), **missing-clause** (F4), **negotiation/redline-adjacent** (F5), **bid comparison** (F6), and **legal review** (5-mode analysis) needs — backed by a real Canadian-procurement knowledge base. The remaining work is mostly **completing workflows, adding proactive runtime (alerts/monitoring), widening document-type coverage, and adding the sourcing front-end & vendor/SRM layer** — not building from zero.

---

## 5. Feature ↔ requirement ↔ gap matrix (revised against real inventory)

Legend — **Build state:** ✅ substantially built · 🟡 partial / adjacent / data-present-but-workflow-thin · 🔴 absent.

| R# | Requirement | Current Lexara capability | State | Gap to close |
|---|---|---|---|---|
| R01 | Requirement intake → structured spec | F2 Workbench intake (intent, commodity, jurisdiction, value, constraints) | 🟡 | Pre-spec "statement of need" + make/buy step ahead of the SOW |
| R02 | Market/supply research synthesis | TED/OCP ingestion + `learning` + FAISS | 🟡 | Aggregate tenders → market views; supplier/price extraction; research-brief generator |
| R03 | Should-cost / TCO | — (thresholds only) | 🔴 | Cost-model templates + benchmark/price data |
| R04 | **Method recommendation** | `ProcurementFramework.allowed_methods` + thresholds + `sole_source_grounds` + Workbench warnings | 🟡 | Turn the data into an explicit *recommender* (method × value × risk × trade-agreement) with rationale |
| R05 | Supplier long/short-list | `Tender.buyer/supplier` + vendor-count estimation | 🟡 | Supplier extraction/dedup from awards; ranking; profiles |
| R06 | **RFx generation** (RFP/RFT/RFQ/RFSQ/RFI) | F2 Workbench drafts **SOW/scope** sections; methods enum; templates | 🟡 | Extend from SOW-only to **full solicitation package** (instructions to bidders, T&Cs, forms); add **RFI** and **RFSQ/prequalification**; one-click full-document export per RFx type |
| R07 | **Evaluation framework builder** | `EvaluationTemplate` (weighted criteria per commodity/method) | 🟡 | Interactive builder (mandatory/rated/weights/price-formula) + validation |
| R08 | T&C/clause assembly + compliance check | `KnowledgeArticle.mandatory_clauses`, `risk_if_omitted`, constraint warnings | 🟡 | Assemble full T&Cs + **Contract-A / trade-agreement** consistency checks |
| R09 | Q&A / addenda mgmt | — | 🔴 | Bidder Q&A intake + versioned addendum issue/reissue |
| R10 | Bid compliance screen | F4 dark-obligation + analysis | 🟡 | Mandatory-criteria pass/fail checklist against a received bid |
| R11 | Evaluation/scoring workbook + report | F6 bid stress-test (obligation matrices); analysis | 🟡 | Multi-evaluator scoring, consensus, **defensible evaluation report** |
| R12 | Award + debrief generation | summary/recommendation generation | 🔴 | Award-rec + debrief-letter templates |
| R13 | Contract assembly + kickoff | clause/knowledge library, F1 portfolio | 🔴 | Bid→contract assembly; schedules; kickoff package; handoff PO→CM |
| R14 | **Obligation extraction → register** | F1/F3 (`obligation_extractor`, `Obligation` model, both-party typing) | ✅ | Polish; promote proposals→register UX |
| R15 | **Key-date / renewal / notice alerts** | F3 resolves dates (business-day/holiday); SMTP config present | 🟡 | **Scheduler + firing notifications** (compute exists; proactive alerting not wired) |
| R16 | Milestone/SLA/KPI tracking | `SLATemplate` (definitions) | 🟡 | **Runtime** SLA/KPI monitoring + performance dashboards (templates ≠ live tracking) |
| R17 | Change/variation/amendment log | F5 clause versions; F1 CRUD | 🟡 | Explicit variation/amendment workflow + diff/redline view |
| R18 | Compliance currency (insurance/bond/WSIB/cert) | `Obligation.obligation_type` (data_handling/reporting…) | 🟡 | Add cert/insurance obligation types + expiry tracking + alerts |
| R19 | Vendor master / segmentation / scorecards | vendor-count, counterparty roles, `Tender` supplier | 🟡→🔴 | **Supplier entity/master**, Kraljic segmentation, performance scorecards, spend view |
| R20 | Closeout / renew-vs-recompete | F1 status + analysis | 🔴 | Closeout templates; recompete decision support |
| R21 | **Contract review / risk / redline** | 5-mode analysis + F5 clause versions (orig/proposed/opponent/agreed) | ✅/🟡 | **Diff rendering + Word tracked-changes round-trip** (versions stored; not rendered) |
| R22 | Clause library / playbook | `KnowledgeArticle` + clause library (1000+) + F5 non-negotiables/tradeables | 🟡 | **User-editable per-tenant** playbook (preferred + fallback) |
| R23 | Missing-clause / off-market detection | **F4 Dark Obligation Detector** (FAISS + peer frequency) | ✅ | Replace conservative estimates with **live** peer frequencies |
| R24 | Risk memo with citations | analysis + `JurisprudenceArticle` + `citation_service` | 🟡 | Wire case-law/source citations into an exportable **risk memo** |
| R25 | Audit trail / versioning / RBAC | `AuditLog`, `User.role` (admin/procurement/legal), JWT | 🟡 | Matter-level versioning + enforced **role-based access** |
| R26 | Jurisdiction/sector context engine | `Jurisdiction` + commodity taxonomy + `ProcurementFramework` + bilingual fields | ✅/🟡 | Add **CCDC (construction)** & IT-MSA packs; render bilingual; widen provinces |
| R27 | Guided (non-lawyer) vs. power (lawyer) mode + "not legal advice" | linter + Workbench guidance (guided); analysis/F5 (power) | 🟡 | Explicit **mode toggle**, logged "not legal advice" acknowledgement |

**Headline gaps (true gaps, now that the platform is correctly inventoried):**
1. **Sourcing front-end is the thinnest** — no should-cost (R03), market-research *synthesis* (R02), explicit method *recommender* (R04 — data present), or supplier shortlisting (R05). This is the **Strategic Sourcing Advisor's** core need and Lexara's biggest white space.
2. **Bidding workflow middle is missing** — Q&A/addenda (R09), defensible multi-evaluator scoring & evaluation report (R11), award/debrief (R12), bid→contract assembly (R13). The PO can *draft* (F2) but can't yet *run the competition to award* end-to-end.
3. **Runtime/proactive layer** — dates are computed (F3) but **alerts don't fire** (R15); SLAs are *templated* but not *monitored* (R16); insurance/bond/WSIB currency (R18) not tracked. CLM is strong at structure, weak at "tell me before it lapses."
4. **Lawyer power-tools last mile** — redline **versions exist but aren't rendered/round-tripped to Word** (R21); playbook is system-owned not **tenant-editable** (R22); citations exist but no **exportable risk memo** (R24).
5. **Vendor/SRM layer** — no supplier master/segmentation/scorecards (R19).
6. **Binding layer** — full **RBAC enforcement**, matter-level versioning (R25), and the explicit **guided vs. power / "not legal advice"** UX (R27).

---

## 6. Prioritized build roadmap (waves) — revised

Sequenced to *complete* what's started before opening new fronts, respect PIPEDA ("no contract text stored by default" → design review before new persistence — CLAUDE.md rule 6), and give each role an end-to-end slice.

- **Wave 1 — Finish the runtime/proactive layer (Contracts Manager, fastest ROI).** Wire **R15 alerts** (scheduler + the already-present SMTP) onto F3's resolved dates; add **R18** insurance/bond/WSIB/cert expiry tracking; surface **R16** SLA monitoring from `SLATemplate`. Leverages F1/F3 + obligation models that already exist — mostly *activation*, not new modeling.
- **Wave 2 — Lawyer power-tools last mile (LAW, high willingness-to-pay).** **R21** diff/redline rendering + **Word tracked-changes round-trip** over F5's stored clause versions; **R22** tenant-editable playbook; **R24** citation-backed risk-memo export using `JurisprudenceArticle`. Pairs with the "speed up drafting/review" promise in the brief.
- **Wave 3 — Complete the bidding workflow (Procurement Officer).** Extend F2 from SOW to **full RFx package** + add **RFI/RFSQ** (R06); ship the **R07** evaluation-framework builder; **R11** multi-evaluator scoring + evaluation report (build on F6); **R09** addenda; **R12** award/debrief; **R13** bid→contract assembly + PO→CM handoff.
- **Wave 4 — Sourcing front-end (Strategic Sourcing Advisor — the white space).** **R04** method *recommender* over existing `ProcurementFramework` data; **R02** market-research synthesis over TED/OCP ingestion (+ CanadaBuys); **R03** should-cost; **R05** supplier shortlisting; **R01** statement-of-need/make-buy intake.
- **Wave 5 — Vendor/SRM + binding layer.** **R19** supplier master/segmentation/scorecards; **R25** RBAC enforcement + matter-level versioning; **R27** explicit guided/power modes + "not legal advice"; **R20** closeout. Knit F1–F6 onto the **Matter/Engagement spine** (§1) so requirement→solicitation→bid→contract→obligations never re-keys.

Cross-cutting: **R26** add CCDC/IT-MSA sector packs + render bilingual; keep **jurisdiction/source attribution** on every output.

---

## 7. Knowledge sources required to build

Lexara's defensibility is its **knowledge base**. (★ = already ingested/modeled in repo; ☆ = schema/partial present, needs population/expansion.)

### 7.1 Clause, contract & template corpora
- ★ **SACC — Standard Acquisition Clauses and Conditions** (PSPC): basis of `lexara_training_data.json` and `KnowledgeArticle.source=SACC`. Keep versioned; widen coverage.
- ☆ **Ontario BPS** — Broader Public Sector Procurement Directive + OPS/MGS vendor-of-record/RFx templates (`source=BPS_DIRECTIVE` exists).
- **CUAD** corpus (510 public contracts) — ★ already powering F4 peer-frequency; move from conservative estimates to **live** frequencies per contract type.
- **Construction — CCDC/CCA** (CCDC 2, 5B…) and **engineering (ACEC)**: *not yet present* — needed for construction-sector breadth.
- **IT/digital** MSAs, SaaS terms, DPAs; **commercial** templates (NDA/MSA/SOW) for private-sector breadth.
- **Provincial/municipal (MASH)** template libraries — CanadaBuys, MERX, bids&tenders, Biddingo.

### 7.2 Legal & regulatory knowledge
- ☆ **Procurement case law** — `JurisprudenceArticle` model exists; populate with *R. v. Ron Engineering* (Contract A/B), duty-of-fairness line, **CITT** bid-protest decisions. Source: **CanLII**.
- ★/☆ **Trade agreements & thresholds** — CFTA/CUSMA/CETA thresholds already in `ProcurementFramework`; add **CPTPP, WTO-GPA**; keep thresholds current.
- **Privacy/data** — PIPEDA + Ontario; data-handling clause standards (ties to Lexara's own storage rule).
- **Sector regulation** — health, defence/controlled goods, financial.

### 7.3 Market & supplier intelligence (for the SSA white space)
- ★ **TED + OCP/OCDS** tender/award open data — already ingested. Add **CanadaBuys** + provincial portals + **historical awards** for supplier discovery, price benchmarks, should-cost.
- **Supplier/firmographic & risk data** — registries, financial health, sanctions/debarment, ESG/diversity certs.
- **Commodity/price indices** for should-cost/TCO.

### 7.4 Process & taxonomy knowledge
- ★ **Commodity taxonomy** — `CommoditySector/Category/Subcategory` present; consider aligning to **UNSPSC**.
- ☆ **Procurement-method decision rules** — data in `ProcurementFramework`; encode as a recommender (R04).
- ☆ **Evaluation methodology** — `EvaluationTemplate` present; expand mandatory/rated/weighted + price-formula library.
- ★/☆ **CLM obligation taxonomy** — `Obligation.obligation_type` enum present; extend (insurance/bond/cert) for R18.
- **SRM frameworks** — Kraljic segmentation + scorecard KPIs (for R19, not yet modeled).

### 7.5 Internal/organizational knowledge (per customer)
- Tenant's own **clause playbook** (preferred + fallback), templates, thresholds, delegation-of-authority, approved-supplier lists — ingested per tenant with **RBAC + PIPEDA-safe** handling (R22/R25).

---

## 8. Compliance & guardrails (must hold across every feature)

- **"AI assistance, not legal advice."** Critical given the non-lawyer-first audience — explicit boundary, logged acknowledgement, lawyer-in-the-loop affordances (R27).
- **PIPEDA / no-contract-text-by-default** (CLAUDE.md rule 6): F1/F2/F3 already persist contract/obligation content per-tenant — any *new* persistence (tenant playbooks, repositories, OCR'd docs) needs the flagged **design review**, and existing storage should be confirmed against this rule.
- **Ontario-first, province-aware** (CLAUDE.md rule 5): the `Jurisdiction`/`ProcurementFramework` models are the right place to extend — don't collapse provincial variation into generic "Canadian" logic.
- **Defensibility & audit** (R25): public procurement is litigated (Contract A, CITT) — every generated document, score, and suggestion needs audit trail + versioning. `AuditLog` exists; enforce RBAC on top.
- **Jurisdiction/source attribution** on every output (already modeled via `jurisdiction` + `source` + `JurisprudenceArticle`) — surface as citations (R24).

---

## 9. One-page summary

- **Roles form a relay:** SSA (strategy) → PO (bid docs) → CM (obligations), with the **Lawyer** (retainer) providing legal assurance across all phases and **Vendor Management** in parallel. All are commodity/sector generalists across public *and* private procurement; Lexara serves non-lawyers first and accelerates lawyers.
- **Lexara today is much further along than a "contract analyzer":** a **6-feature platform** (Portfolio Obligation Index, SOW Workbench, Obligation Matrix, Dark Obligation Detector, Negotiation Simulator, Bid Stress-Test) on a **real Canadian-procurement knowledge layer** (SACC/BPS clauses, trade-agreement thresholds, allowed-methods, jurisprudence, commodity & jurisdiction taxonomies). It already partially serves **all five roles**.
- **The true gaps are at the two ends and in the runtime:** the **sourcing front-end** (should-cost, market-research synthesis, method recommender, supplier shortlisting) is the biggest white space (SSA); the **bidding middle** (addenda, defensible scoring, award/debrief, bid→contract) is incomplete (PO); the **proactive runtime** (renewal/notice alerts, live SLA & insurance-currency monitoring) needs activating (CM); **lawyer power-tools** (Word redline round-trip, editable playbook, risk-memo export) need the last mile; and **vendor/SRM + RBAC + the matter spine** bind it all.
- **Build order:** activate CLM runtime/alerts (W1) → lawyer redline/playbook/memo (W2) → complete bidding workflow (W3) → sourcing front-end (W4) → vendor/SRM + RBAC + matter spine + dual-mode (W5).
- **Moat = knowledge:** extend SACC + BPS + CCDC + IT-MSA corpora, populate `JurisprudenceArticle` (Contract A / CITT via CanLII), keep trade-agreement thresholds current, widen TED/OCP with CanadaBuys + awards, add UNSPSC alignment and per-tenant playbooks — all under PIPEDA and an explicit "not legal advice" boundary.
