# Lexara — Feature Design & Build Plan (5-Wave Roadmap)

_Status: Build-planning / architecture. Author: product architect. Date: 2026-06-04._
_Source of truth: `docs/procurement-roles-and-feature-map.md` (R01–R27, F1–F6, §6 waves, §7 knowledge sources). Architecture authority: `CLAUDE.md`._

This document turns §6's five-wave roadmap into an actionable, buildable plan. It does **not** restate the analysis — it builds on it, referencing R## and F# IDs. Every design conforms to CLAUDE.md: **thin routers → one service call → HTTP out**, **all config via `app/config.py` env vars**, **Alembic-only migrations** (new revision files; never edit committed ones; `alembic/versions/` is treated as frozen-once-committed), **LLM waterfall Groq → HF/SaulLM → Claude** with **per-tier prompt formats**, **Ontario-first / province-aware**, and **PIPEDA "no contract text stored by default"** — any new persistence of contract/clause content is flagged **[PIPEDA-REVIEW]**.

A recurring tension drives the sequencing: three **foundational enablers** (scheduler/notification, the Matter/Engagement spine, RBAC) are nominally "Wave 5," but Waves 1–4 depend on them. The resolution is in §1 and §8: **build thin vertical slices of the enablers early**, ahead of their full Wave-5 build-out.

---

## 0. Conventions used in this plan

- **Effort** — S (≤3 dev-days), M (1–2 wk), L (2–4 wk), XL (>4 wk), per feature, one engineer.
- **Service naming** — `app/services/<area>_service.py` with verb-first functions; routers stay thin.
- **Migrations** — each schema delta = one new Alembic revision: `alembic revision --autogenerate -m "..."` → review → `alembic upgrade head`. Column adds to existing tables are additive/nullable to keep deploys non-breaking.
- **LLM rule** — rules-first, LLM-second. Deterministic logic (thresholds, business-day math, weight sums, frequency counts) is **never** delegated to an LLM. LLM is used only for drafting/synthesis/classification, always through `analyze_with_llm`-style waterfall wrappers, with prompt format chosen **per tier** (Groq = OpenAI chat; HF/SaulLM = Alpaca `### Instruction/### Input/### Response`; Claude = Messages API).
- **"Not legal advice"** — every generated legal artifact carries the boundary string and, where the user acts on it, a logged acknowledgement (R27).

---

## 1. Foundational enablers (designed once, reused across all waves)

These are cross-cutting. They are specified here first because almost every wave feature consumes them. **Recommendation: ship the MVP slice of each enabler in the milestone that first needs it (see §8 critical path), not in Wave 5.**

### E1 — Scheduler & Notification service  `[enables W1, W3, W5]`

**Why early:** R15/R16/R18 alerts (Wave 1) cannot fire without it; W3 closing-date/addendum reminders and W5 QBR cadences reuse it.

- **Data model (new):**
  - `notification_rules` — `id`, `user_id` (FK users), `matter_id` (FK matters, nullable), `entity_type` (`obligation|sla_kpi|compliance_item|solicitation|supplier_review`), `entity_id`, `rule_type` (`lead_time|recurrence|threshold_breach`), `lead_days` (int), `channel` (`email|in_app`), `is_active`, `created_at`.
  - `notifications` — `id`, `user_id`, `rule_id` (FK), `entity_type`, `entity_id`, `fire_at` (DateTime), `status` (`pending|sent|failed|acknowledged`), `payload_json`, `sent_at`, `created_at`. The `(status, fire_at)` index drives the poller.
- **Service:** `app/services/notification_service.py` — `compute_due_notifications(db, now)` (pure, returns rows to fire), `enqueue_notification(...)`, `dispatch_pending(db)` (sends via existing SMTP config: `settings.smtp_server/port/username/password`), `acknowledge(notification_id)`.
- **Runner:** an APScheduler `AsyncIOScheduler` started in the FastAPI lifespan (single VPS → in-process is fine for MVP; document that horizontal scale needs a DB advisory-lock or external beat). Tick interval via new env `SCHEDULER_TICK_SECONDS` (default 300) in `app/config.py`. Reuses the same "flag + interval" config idiom as the HF warmer.
- **Config additions:** `notifications_enabled: bool = False`, `scheduler_tick_seconds: int = 300`, `notify_from_email: Optional[str]`.
- **PIPEDA:** payloads store **metadata only** (dates, names, dollar figures) — never clause text. No review needed if this rule holds; flagged in DoD checklist.

### E2 — Matter / Engagement spine  `[enables every wave; full build W5]`

The §1 spine: one object threading requirement → solicitation → bid → contract → obligations so nothing is re-keyed.

- **Data model (new `app/models/matter.py`):**
  - `matters` — `id` (UUID), `user_id`/`owner_id` (FK users), `org_id` (FK orgs, see E3), `title`, `reference_no`, `jurisdiction_code`, `commodity_category_code`, `procurement_method`, `estimated_value_cad`, `phase` (`P0..P8` per §1), `status` (`open|awarded|active|closed`), `created_at`, `updated_at`.
  - `matter_links` — polymorphic join: `id`, `matter_id` (FK), `entity_type` (`workbench_session|negotiation_session|portfolio_contract|solicitation|bid|supplier`), `entity_id`, `role` (`requirement|solicitation|bid|contract|obligation_register`), `created_at`. This avoids adding `matter_id` to six tables at once.
- **Migration strategy:** Phase A (early) — create `matters` + `matter_links`, backfill nothing. Phase B (W5) — add **nullable** `matter_id` columns to `workbench_sessions`, `negotiation_sessions`, `portfolio_contracts` for direct querying, populated lazily. All additive → no break to F1–F6.
- **Service:** `app/services/matter_service.py` — `create_matter`, `link_entity`, `get_matter_thread(matter_id)` (returns the relay timeline), `advance_phase`.
- **PIPEDA:** matters hold metadata, not contract text → no review.

### E3 — RBAC & multi-tenant org model  `[enforced W5; thin slice early]`

`User.role` (`admin|procurement|legal`) exists but is **not enforced**. Public procurement is litigated (Contract A, CITT) → defensible role-scoped access is required (R25).

- **Data model:** add `organizations` (`id`, `name`, `created_at`); add nullable `org_id` to `users` (additive migration). Extend role vocabulary to the five operating roles: `admin | sourcing | procurement | contracts | legal | vendor_mgmt | viewer`. Add `matter_members` (`matter_id`, `user_id`, `role`, `permissions_json`) for per-matter scoping.
- **Service / dependency:** `app/security.py` is **frozen — do not edit**. Add a *new* `app/middleware/rbac.py` with a FastAPI dependency factory `require_role(*roles)` and `require_matter_access(matter_id, action)` that composes on top of the existing `get_current_user`. Routers add the dependency; no change to the frozen auth/JWT code.
- **Early slice (M1):** define the role enum + `require_role` dependency and apply it non-blocking (log-only / soft mode) so later features can adopt it incrementally; flip to hard-enforce in W5.

### E4 — Document assembly / DOCX round-trip service  `[enables W2, W3]`

Redline round-trip (R21) and full-RFx export (R06/R12) both need DOCX in/out with tracked changes.

- **Service:** `app/services/document_service.py` — `assemble_docx(sections: list[dict]) -> bytes` (build from knowledge-article/template blocks), `render_redline_docx(original, revised, comments) -> bytes` (emit `w:ins`/`w:del` tracked-change runs), `parse_docx(bytes) -> structured_clauses` (extend the existing `upload.py` extractor). Library: `python-docx` for assembly; for true tracked-change XML, a thin `docx`-XML writer (documented limitation: complex source formatting is normalized).
- **No new persistent tables** — operates on request payloads and existing stored clause versions (F5 `NegotiationClause.original_text/your_proposed_text/agreed_text`). Generated files are streamed, **not stored** → PIPEDA-safe by default.

### E5 — Per-tenant knowledge / playbook store  `[enables W2; reused W3/W5]`  `[PIPEDA-REVIEW]`

R22 needs a **tenant-editable** playbook (preferred + fallback positions) layered over the system `KnowledgeArticle` library.

- **Data model (new):** `tenant_playbook_clauses` — `id`, `org_id` (FK), `clause_type`, `clause_key`, `position` (`preferred|fallback|walk_away`), `title`, `body_text`, `rationale`, `risk_if_omitted`, `source_article_id` (nullable FK to `knowledge_articles.article_id`), `is_active`, `version`, `created_by`, `created_at`. A `tenant_thresholds` table mirrors `ProcurementFramework` overrides per org.
- **Resolution rule:** lookups return tenant override **if present**, else fall back to the system `KnowledgeArticle`. Service: `app/services/playbook_service.py` — `resolve_clause(org_id, clause_type, position)`, `upsert_playbook_clause`, `diff_against_system`.
- **[PIPEDA-REVIEW]:** this **persists customer-authored clause/contract language** → triggers the CLAUDE.md rule-6 design review before build. Mitigation: org-scoped, RBAC-gated, no cross-tenant reads, encryption-at-rest confirmed.

---

## 2. Wave 1 — Finish the CLM runtime / proactive layer  (Contracts Manager; fastest ROI)

> Goal: F1/F3 already *compute* dates and *template* SLAs; W1 makes Lexara **tell you before something lapses**. Mostly activation over existing models + E1.

### W1.1 — Key-date / renewal / notice alerts  (R15)  — CM

- **User stories:** _As a Contracts Manager,_ I get an email N days before any renewal window, notice deadline, or auto-renew trigger so I never miss one. _As a lawyer,_ I see the same dates on matters I advise, scoped by RBAC.
- **Scope in (MVP):** lead-time email/in-app alerts on (a) `Obligation` rows with `absolute_deadline` or resolved `obligation_temporal_resolutions.projected_date`; (b) renewal/notice obligation types. **Out (later):** SMS, calendar (.ics) sync, escalation chains.
- **Data model:** reuse `Obligation`, `ObligationTemporalResolution`. New `notification_rules`/`notifications` from **E1**. Extend `Obligation.obligation_type` vocabulary (string col, no DDL) to include `auto_renew`, `option_exercise`, `notice_window`.
- **API:** `POST /v1/contracts/{id}/alerts` → `notification_service.create_rules_for_contract`; `GET /v1/alerts` → `list_notifications`; `POST /v1/alerts/{id}/ack` → `acknowledge`. Thin routers only.
- **Services / logic:** **rules only** — when a resolution date or `absolute_deadline` exists, compute `fire_at = date - lead_days` (business-day aware via the existing resolver/`holidays` table). No LLM. Dispatch via E1 over SMTP.
- **Knowledge to populate (§7.4):** holiday tables per jurisdiction (Ontario + federal first); standard notice-period defaults per contract type.
- **Dependencies:** **E1 (hard)**. F3 resolver (exists).
- **Acceptance:** given an obligation due 2026-07-01 and a 30-day rule, a `notifications` row fires on the correct **business day**; ack flips status; no alert fires twice.
- **Effort:** **M.**  Milestone: first feature after E1.
- **Risks:** in-process scheduler missed ticks (mitigate: catch-up query on startup scanning overdue `fire_at`); email deliverability (mitigate: log failures, retry, surface in-app).

### W1.2 — Compliance-currency tracking: insurance / bond / WSIB / certifications  (R18)  — CM, VM, LAW

- **User stories:** _As a CM,_ I track each vendor's insurance/bond/WSIB/cert expiry and get alerted before lapse.
- **Scope in (MVP):** a compliance-item register with expiry dates + alerts. **Out:** automated certificate ingestion/OCR.
- **Data model:** **extend `Obligation.obligation_type`** with `insurance|bond|wsib|certification` (string vocab, no DDL) **and** add nullable columns via one additive migration: `Obligation.expiry_date (Date)`, `Obligation.coverage_amount_cad (Float)`, `Obligation.issuer (String)`, `Obligation.compliance_status (String: current|expiring|lapsed)`. Reuses the same obligation row + cascade scans (F1).
- **API:** `POST /v1/contracts/{id}/compliance-items`, `GET /v1/compliance/dashboard` (status roll-up). Service `compliance_service.py`.
- **Logic:** rules — `compliance_status` derived from `expiry_date` vs now; alerts via E1. No LLM (optional LLM-assist later to *extract* expiry from pasted cert text → would be [PIPEDA-REVIEW]).
- **Knowledge (§7.4):** obligation-taxonomy extension (insurance/bond/cert) per the analysis.
- **Dependencies:** E1; W1.1 alert plumbing.
- **Acceptance:** an item expiring in 14 days with a 30-day rule shows `expiring` and has fired an alert.
- **Effort:** **M.**
- **Risks:** data-entry burden (mitigate: pre-seed standard item types per commodity from `CommoditySubcategory.special_requirements`).

### W1.3 — Live SLA / KPI monitoring  (R16)  — CM, VM

- **User stories:** _As a CM,_ I instantiate a `SLATemplate` against a live contract and log periodic measurements; breaches alert and roll into a performance view.
- **Scope in (MVP):** instantiate KPIs from `SLATemplate.kpis`; manual/period measurement entry; breach flagging + alert; simple dashboard. **Out:** automated metric ingestion, service-credit auto-calc beyond `remedy_formula` display.
- **Data model (new):** `contract_sla_instances` (`id`, `contract_id` FK, `sla_template_id`, `kpi_id`, `target_value`, `reporting_frequency`, `is_active`); `sla_measurements` (`id`, `instance_id` FK, `period_start`, `period_end`, `measured_value`, `is_breach`, `recorded_by`, `created_at`).
- **API:** `POST /v1/contracts/{id}/sla/instantiate` (from template), `POST /v1/sla/{instance}/measurements`, `GET /v1/contracts/{id}/sla/dashboard`. Service `sla_service.py`.
- **Logic:** rules — breach = comparator on `measured_value` vs `target_value`; recurrence reminders via E1 from `reporting_frequency`. No LLM.
- **Knowledge (§7.4):** expand `SLATemplate` KPI library per commodity (evaluation methodology / KPI sets).
- **Dependencies:** E1; `SLATemplate` (exists).
- **Acceptance:** instantiating a template creates one instance per KPI; a measurement below target flags breach and emits an alert; dashboard shows breach %.
- **Effort:** **M→L.**
- **Risks:** breach-comparator direction varies by KPI (higher-is-better vs lower-is-better) — store a `comparator` field on the KPI descriptor.

---

## 3. Wave 2 — Lawyer power-tools last mile  (LAW; high willingness-to-pay)

> Goal: F5 stores clause versions but doesn't render/round-trip them; playbook is system-owned; citations exist but no exportable memo.

### W2.1 — Diff/redline rendering + Word tracked-changes round-trip  (R21)  — LAW, PO, CM

- **User stories:** _As a lawyer,_ I upload a counterparty draft, see a clause-by-clause diff vs our standard, and export a `.docx` with tracked changes + margin comments. _As a PO,_ guided mode shows plain-language "what changed and why."
- **Scope in (MVP):** render diffs over F5 `NegotiationClause` versions (`original_text` vs `your_proposed_text`/`agreed_text`); DOCX export with `w:ins`/`w:del`. **Out:** full-fidelity formatting preservation; multi-author merge.
- **Data model:** **none new** — reuse F5 versions. Optional `NegotiationClause.redline_comment (Text)` additive column for the exported margin note. DOCX is streamed, not stored → PIPEDA-safe.
- **API:** `GET /v1/negotiation/{session}/redline` (JSON diff for UI), `POST /v1/negotiation/{session}/export/docx` → `document_service.render_redline_docx`. Thin routers.
- **Logic:** **rules** for the diff (token/sentence diff is deterministic — do **not** use an LLM to compute diffs); **LLM** only to draft the plain-language "why this changed" rationale (Groq→HF→Claude; Claude prompt mirrors `_prompt_extract_clauses`).
- **Knowledge:** none new for the diff; rationale draws on `KnowledgeArticle.guidance_note`.
- **Dependencies:** **E4 (hard)**; F5 (exists).
- **Acceptance:** export opens in Word with native tracked changes accept/reject; diff endpoint marks insertions/deletions correctly; rationale present per changed clause.
- **Effort:** **L** (DOCX tracked-change XML is fiddly).
- **Risks:** DOCX tracked-change XML edge cases (mitigate: golden-file tests opened in Word + LibreOffice); "not legal advice" boundary must be on every export.

### W2.2 — Tenant-editable clause playbook  (R22)  — LAW, PO  `[PIPEDA-REVIEW]`

- **User stories:** _As a lawyer,_ I curate our preferred + fallback positions per clause type; review then compares incoming clauses to **our** standard, not just the generic library.
- **Scope:** CRUD over `tenant_playbook_clauses` (**E5**); wire `playbook_service.resolve_clause` into the redline/comparison path (W2.1) and F5 non-negotiables/tradeables. **Out:** AI-suggested playbook authoring (later).
- **Data model:** **E5** tables. `[PIPEDA-REVIEW]` — persists customer clause text.
- **API:** `GET/POST/PATCH/DELETE /v1/playbook/clauses`, `GET /v1/playbook/diff?clause_type=` → `playbook_service`.
- **Logic:** rules (override-or-fallback resolution); LLM optional for "does this deviate from our standard and how" (classification → Groq first).
- **Knowledge (§7.5):** per-tenant clause playbook ingestion, RBAC + PIPEDA-safe.
- **Dependencies:** **E5 (hard, incl. design review)**, **E3** (org scoping).
- **Acceptance:** a playbook override is returned in preference to the system article; deletion reverts to system default; cross-tenant read blocked.
- **Effort:** **M** (+ design-review lead time for E5).
- **Risks:** legal/compliance — storing tenant contract language; mitigate via E5 review, org isolation, audit on every read/write.

### W2.3 — Citation-backed risk-memo export  (R24)  — LAW

- **User stories:** _As a lawyer,_ I generate an exportable risk memo: each flagged risk cites the source clause and relevant `JurisprudenceArticle` (Contract A / CITT), validated by `citation_service`.
- **Scope in (MVP):** assemble memo from existing 5-mode `key_risks` + `JurisprudenceArticle` matches by `clause_types`/`jurisdiction_codes`; McGill-format citations via `citation_service`; export DOCX/PDF. **Out:** auto-pulling new CanLII cases at request time.
- **Data model:** none new (reads `JurisprudenceArticle`). Memo streamed, not stored.
- **API:** `POST /v1/analysis/{id}/risk-memo` → `risk_memo_service.build_memo`. Thin router.
- **Logic:** rules — match jurisprudence by clause type + jurisdiction, validate citations; **LLM** to draft prose around each risk (waterfall). Boundary string mandatory.
- **Knowledge (§7.2):** **populate `JurisprudenceArticle`** — *R. v. Ron Engineering* (Contract A/B), *Tercon*, duty-of-fairness line, **CITT** bid-protest decisions, via **CanLII**. This is a knowledge-seeding task, not just code.
- **Dependencies:** E4 (export); `citation_service`, `JurisprudenceArticle` (exist, under-populated).
- **Acceptance:** memo lists each risk with a valid McGill citation and a real jurisprudence reference where one exists; carries "not legal advice."
- **Effort:** **M** (S code + M data-seeding).
- **Risks:** data-quality / hallucinated citations — **never** let the LLM invent citations; citations come only from the DB + `citation_service` validation.

---

## 4. Wave 3 — Complete the bidding workflow  (Procurement Officer)

> Goal: the PO can *draft* (F2) but can't *run the competition to award*. W3 fills the middle.

### W3.1 — Full RFx package generation + RFI / RFSQ  (R06)  — PO, LAW

- **User stories:** _As a PO,_ from a Workbench session I generate a complete solicitation (instructions to bidders, T&Cs, SOW, mandatory forms), and I can start an RFI or RFSQ/prequalification, not just an SOW.
- **Scope in (MVP):** extend F2 from SOW-only to full-package assembly using `SOWTemplate` + `KnowledgeArticle` (`section_type = terms_conditions`, etc.); add **RFI** and **RFSQ** templates; one-click DOCX export per RFx type. **Out:** portal auto-posting.
- **Data model:** new `SOWTemplate` rows (RFI, RFSQ) — **data, not schema**. Optionally generalize naming via a `document_type` field on a new `solicitations` table (see W3.5). `WorkbenchSession.procurement_method` already supports the method enum.
- **API:** `POST /v1/workbench/{session}/assemble-package`, `GET /v1/workbench/templates?method=RFI` → `workbench_service` (extend existing functions, keep thin router). Export via E4.
- **Logic:** rules — section selection from template + mandatory-clause gating by threshold/method; **LLM** for section *drafting* (existing `draft_section_text`, waterfall).
- **Knowledge (§7.1):** SACC ★, **BPS** templates ☆, RFI/RFSQ section blueprints; **CCDC** for construction T&Cs.
- **Dependencies:** E4; F2 (exists).
- **Acceptance:** an RFP session exports a multi-section package incl. instructions-to-bidders + T&Cs; an RFI session uses the RFI template; mandatory clauses appear above threshold.
- **Effort:** **L.**
- **Risks:** template breadth/data-quality (mitigate: start IT + services + construction; flag uncovered commodity/method combos).

### W3.2 — Evaluation-framework builder  (R07)  — PO

- **User stories:** _As a PO,_ I build mandatory/rated criteria with weights, scoring scales, and a price formula, validated for consistency and CFTA disclosure.
- **Scope in (MVP):** interactive builder seeded from `EvaluationTemplate.criteria`; weight-sum validation; price-method picker; export of the evaluation plan. **Out:** evaluator portal (→ W3.3).
- **Data model (new):** `evaluation_plans` (`id`, `matter_id`/`session_id`, `award_methodology`, `criteria_json`, `price_formula`, `cfta_disclosed`, `version`, `created_by`). Built **from** `EvaluationTemplate`.
- **API:** `POST /v1/evaluation/plans`, `PATCH /v1/evaluation/plans/{id}`, `GET /v1/evaluation/plans/{id}/validate` → `evaluation_service`.
- **Logic:** **rules** — weights sum to 100, mandatory vs rated separation, CFTA Art. 509 disclosure check (deterministic). No LLM for math; optional LLM to suggest criteria text.
- **Knowledge (§7.4):** expand `EvaluationTemplate` library (mandatory/rated/weighted + price-formula library).
- **Dependencies:** E2 (link to matter); `EvaluationTemplate` (exists).
- **Acceptance:** a plan whose weights ≠ 100 fails validation; CFTA-required disclosure flag enforced above threshold.
- **Effort:** **M.**

### W3.3 — Multi-evaluator scoring + defensible evaluation report  (R11)  — PO

- **User stories:** _As a PO,_ multiple evaluators score each bid against the plan; I run consensus and produce a defensible evaluation report. Builds on **F6** (bid stress-test obligation matrices).
- **Scope in (MVP):** per-evaluator scores, consensus capture, score roll-up, evaluation-report export with full audit trail. **Out:** anonymized blind scoring, statistical outlier detection.
- **Data model (new):** `bids` (`id`, `matter_id`, `bidder_name`, `received_at`, `status`); `bid_scores` (`id`, `bid_id`, `evaluation_plan_id`, `evaluator_id`, `criterion_id`, `score`, `rationale_text`, `created_at`); `evaluation_consensus` (`id`, `bid_id`, `criterion_id`, `consensus_score`, `notes`).  `[PIPEDA-REVIEW]` if bid documents are stored — MVP stores **scores + rationales only**, not bid text.
- **API:** `POST /v1/bids`, `POST /v1/bids/{id}/scores`, `POST /v1/bids/{id}/consensus`, `POST /v1/matters/{id}/evaluation-report` → `scoring_service`. Reuse F6 `compare_service` for the obligation-matrix comparison view.
- **Logic:** rules — weighted roll-up, mandatory pass/fail gating, consensus capture (deterministic, audit-logged). LLM only to draft report narrative.
- **Knowledge (§7.2):** Contract-A / duty-of-fairness rules surfaced as guardrails (no undisclosed criteria); CITT defensibility checklist.
- **Dependencies:** **W3.2 (hard — needs the plan)**, **E3 RBAC** (evaluator identity/scoping), **E2** (matter), F6.
- **Acceptance:** a bid failing a mandatory criterion is excluded; report reproduces every evaluator score with timestamp + `AuditLog` entry.
- **Effort:** **L.**
- **Risks:** legal/defensibility — incomplete audit trail is a CITT exposure (mitigate: write `AuditLog` on every score/consensus mutation; immutable score history).

### W3.4 — Bidder Q&A / addenda management  (R09)  — PO

- **User stories:** _As a PO,_ I log bidder questions, draft answers, and issue versioned addenda that adjust the solicitation, with full version history.
- **Scope in (MVP):** Q&A intake, answer drafting, versioned addendum issuance, change log. **Out:** public portal Q&A sync.
- **Data model (new):** `solicitation_questions` (`id`, `matter_id`, `question_text`, `answer_text`, `is_published`, `created_at`); `addenda` (`id`, `matter_id`, `addendum_no`, `summary`, `changes_json`, `issued_at`, `version`).
- **API:** `POST /v1/matters/{id}/questions`, `POST /v1/matters/{id}/addenda`, `GET /v1/matters/{id}/addenda` → `addenda_service`.
- **Logic:** rules — version/sequence integrity; LLM to draft answer/addendum language (waterfall).
- **Dependencies:** E2 (matter), W3.1 (solicitation to amend).
- **Acceptance:** issuing addendum N increments the version and records a diff; published Q&A is immutable once issued.
- **Effort:** **M.**

### W3.5 — Award + debrief generation  (R12)  — PO, LAW

- **User stories:** _As a PO,_ I generate an award recommendation and bidder debrief letters from the evaluation results.
- **Scope:** templates for award-rec + debrief (success/regret), populated from W3.3 results. **Out:** standstill-period automation (alert only, via E1).
- **Data model:** reuse `bids`/`evaluation_consensus`; new `award_decisions` (`id`, `matter_id`, `winning_bid_id`, `rationale`, `standstill_ends_on`, `status`). Standstill end-date feeds E1 alerts.
- **API:** `POST /v1/matters/{id}/award`, `POST /v1/bids/{id}/debrief-letter` → `award_service`. Export via E4.
- **Logic:** rules (pull scores/ranking) + LLM (letter prose). Boundary string on legal-adjacent text.
- **Knowledge (§7.2):** debrief best-practice + standstill obligations.
- **Dependencies:** W3.3, E4, E1 (standstill alert).
- **Acceptance:** award doc names the winner with score rationale; regret letter omits competitor data; standstill alert scheduled.
- **Effort:** **M.**

### W3.6 — Bid → contract assembly + PO→CM handoff  (R13)  — PO, CM

- **User stories:** _As a PO,_ I assemble the executed contract from the winning bid + schedules and hand off to the CM; the obligation register (F1/F3) is pre-populated.
- **Scope in (MVP):** assemble contract doc from awarded SOW + T&Cs + winning-bid schedules; create a `PortfolioContract` + run `obligation_extractor` to seed the register; **link everything on the Matter spine (E2)**. **Out:** e-signature integration.
- **Data model:** reuse `PortfolioContract` + `Obligation`/`ContractObligation`; `matter_links` (E2) record the relay. Contract assembly is the **PO→CM bridge** — this is where Wave 3 meets Wave 1.
- **API:** `POST /v1/matters/{id}/assemble-contract` → `contract_assembly_service` (creates PortfolioContract, calls `extract_obligations_from_text`, links matter).
- **Logic:** rules (assemble from agreed sections) + existing extraction services. PIPEDA: F1/F3 already persist obligation content per-tenant — **confirm** against rule 6; no *new* persistence type.
- **Dependencies:** **E2 (hard)**, W3.1/W3.5, F1/F3 obligation extraction.
- **Acceptance:** assembling a contract creates a `PortfolioContract`, ≥1 `Obligation`, and a `matter_link` of role `contract`; the W1 alert engine then sees its dates.
- **Effort:** **L.**

---

## 5. Wave 4 — Sourcing front-end  (Strategic Sourcing Advisor — the biggest white space)

> Goal: the thinnest area today (R02/R03/R04/R05/R01). Build the SSA's pre-solicitation slice. R04 has data already; R03 needs new data.

### W4.1 — Procurement-method recommender  (R04)  — SSA

- **User stories:** _As an SSA,_ I enter need + value + risk + jurisdiction and get a recommended method (RFP/RFT/RFQ/RFSQ/standing-offer/sole-source) **with rationale**, a threshold/trade-agreement check, and a sole-source justification template if applicable.
- **Scope in (MVP):** deterministic recommender over `ProcurementFramework` (`allowed_procurement_methods`, thresholds, `cfta/cusma/ceta_*_threshold`, `sole_source_grounds`). **Out:** ML ranking.
- **Data model:** reads `ProcurementFramework`, `Jurisdiction`, `CommodityCategory`. New `method_recommendations` (`id`, `matter_id`, `inputs_json`, `recommended_method`, `rationale`, `trade_agreement_flags`, `created_at`) for the audit trail.
- **API:** `POST /v1/sourcing/method-recommendation` → `method_recommender_service.recommend`. Thin router.
- **Logic:** **rules-first** — method = f(value vs thresholds, commodity, allowed methods, trade-agreement applicability, sole-source grounds). Trade-agreement thresholds are deterministic, **never** LLM. LLM only to phrase the rationale narrative (waterfall).
- **Knowledge (§7.4):** encode the **procurement-method decision rules** (data in `ProcurementFramework` → recommender); keep CFTA/CUSMA/CETA thresholds current; add **CPTPP, WTO-GPA** to the framework.
- **Dependencies:** E2 (matter); `ProcurementFramework` (exists, populated).
- **Acceptance:** a $50k IT-services need in ON returns the correct method with the threshold logic shown; an above-CETA value flags trade-agreement obligations; sole-source returns a justification template only when grounds match.
- **Effort:** **M.**
- **Risks:** legal — wrong threshold = bid protest (mitigate: cite the framework row + source on every recommendation; "not legal advice").

### W4.2 — Market / supply-market research synthesis  (R02)  — SSA, VM

- **User stories:** _As an SSA,_ I get a market brief — supplier landscape, recent comparable awards, price ranges, concentration — synthesized from ingested tenders.
- **Scope in (MVP):** aggregate existing `Tender` rows (TED/OCP) + FAISS similarity into a market view (comparable awards, buyer/supplier counts, value distribution); generate a research-brief draft. **Out:** live external API calls at request time.
- **Data model:** reads `Tender`; reuse `nlp/` FAISS + `learning`. New `market_briefs` (`id`, `matter_id`, `query_json`, `findings_json`, `generated_at`).
- **API:** `POST /v1/sourcing/market-brief` → `market_research_service.synthesize`. Thin router.
- **Logic:** rules — aggregation/stats from `Tender`; FAISS for comparables. LLM to write the brief narrative (waterfall).
- **Knowledge (§7.3):** widen ingestion — **CanadaBuys** + provincial portals + **historical awards** alongside existing **TED + OCP/OCDS**.
- **Dependencies:** ingestion pipeline (exists); E2.
- **Acceptance:** a brief for "cloud IaaS, ON" returns ≥N comparable awards with value range + supplier list from real `Tender` data, plus a narrative.
- **Effort:** **L.**
- **Risks:** data-quality/coverage of ingested tenders (mitigate: state coverage/recency in the brief; never fabricate suppliers — list only ingested ones).

### W4.3 — Should-cost / TCO modelling  (R03)  — SSA

- **User stories:** _As an SSA,_ I build a should-cost / TCO model from category templates + benchmark data.
- **Scope in (MVP):** parameterized cost-model templates (cost drivers, TCO horizon) with benchmark inputs; output a should-cost summary. **Out:** live commodity-index feeds.
- **Data model (new):** `cost_model_templates` (`id`, `commodity_category_id`, `drivers_json`); `cost_models` (`id`, `matter_id`, `inputs_json`, `result_json`, `created_at`).
- **API:** `POST /v1/sourcing/cost-models`, `GET /v1/sourcing/cost-models/{id}` → `cost_model_service`.
- **Logic:** **rules** — deterministic arithmetic (TCO, NPV optional). No LLM for the math; optional LLM for assumption commentary.
- **Knowledge (§7.3):** commodity/price indices + benchmark data (new ingestion — biggest data gap in this wave).
- **Dependencies:** new benchmark data; E2.
- **Acceptance:** a model with given drivers returns a reproducible should-cost figure + TCO breakdown.
- **Effort:** **M** (code) **+ L** (benchmark data sourcing).

### W4.4 — Supplier discovery / long-list → short-list  (R05)  — SSA, VM

- **User stories:** _As an SSA,_ I generate a supplier long-list from award history, dedup it, and rank to a short-list.
- **Scope in (MVP):** extract/dedup suppliers from `Tender.supplier`/awards into the **Supplier entity (E6/W5)**; rank by frequency/value/recency. **Out:** financial-health/sanctions enrichment (later, §7.3).
- **Data model:** writes the new **`suppliers`** table (introduced here, fully built in W5.1); `supplier_award_history` (`id`, `supplier_id`, `tender_id`, `value`, `awarded_at`).
- **API:** `POST /v1/sourcing/supplier-shortlist` → `supplier_discovery_service.build_shortlist`.
- **Logic:** rules — dedup (normalized name match), ranking. Optional LLM for fuzzy entity resolution (classification, Groq-first).
- **Knowledge (§7.3):** TED/OCP/CanadaBuys awards; later registries/risk data.
- **Dependencies:** `Tender` (exists); **Supplier entity** (shared with W5.1 — build the table here).
- **Acceptance:** suppliers dedup correctly; short-list ranks by configurable signal; each entry traces to a real award.
- **Effort:** **M.**

### W4.5 — Statement-of-need / make-vs-buy intake  (R01)  — SSA, PO

- **User stories:** _As an SSA,_ I turn a plain-language need into a structured statement-of-need + make/buy step **before** the SOW.
- **Scope in (MVP):** a pre-spec intake (need, outcome vs spec, make/buy prompts) that seeds a Matter and pre-fills the Workbench. **Out:** business-case financial modelling (overlaps W4.3).
- **Data model:** extend Matter (E2) `phase=P0`; new `statements_of_need` (`id`, `matter_id`, `need_text`, `outcome_vs_spec`, `make_buy_decision`, `created_at`).
- **API:** `POST /v1/sourcing/statement-of-need` → `intake_service.create_statement` (creates Matter, links). Feeds `workbench_service`.
- **Logic:** rules + LLM (structure the plain-language need → skeleton; waterfall). Plain-language/guided mode (R27).
- **Dependencies:** **E2 (hard)**, F2 Workbench.
- **Acceptance:** a free-text need produces a structured statement + a Matter in `P0` that flows into a Workbench session.
- **Effort:** **M.**

---

## 6. Wave 5 — Vendor / SRM + binding layer  (RBAC, Matter spine, dual-mode)

> Goal: the SRM layer + the bindings that knit F1–F6 onto the spine. Several pieces are the **full build-out** of enablers seeded earlier.

### W5.1 — Supplier master / segmentation / scorecards  (R19)  — VM, CM, SSA

- **User stories:** _As a VM,_ I maintain a supplier master, segment via Kraljic, run performance + risk scorecards, and see consolidated spend & contract footprint per supplier.
- **Scope in (MVP):** supplier master (built on W4.4 `suppliers`), Kraljic segmentation, scorecards (perf + risk), spend roll-up across `PortfolioContract`/awards. **Out:** automated firmographic/ESG enrichment.
- **Data model:** finalize **`suppliers`** (`id`, `org_id`, `name`, `normalized_name`, `segment` (`strategic|leverage|bottleneck|routine`), `risk_rating`, `status`, `created_at`); `supplier_scorecards` (`id`, `supplier_id`, `period`, `kpi_scores_json`, `risk_score`, `created_at`). Link suppliers↔contracts via `matter_links` / a `contract_id` FK.
- **API:** `GET/POST /v1/suppliers`, `POST /v1/suppliers/{id}/scorecards`, `GET /v1/suppliers/{id}/footprint` → `supplier_service`.
- **Logic:** rules — Kraljic placement (spend × supply-risk matrix), spend aggregation. LLM optional for risk-note synthesis.
- **Knowledge (§7.4):** **Kraljic segmentation** + scorecard KPI frameworks (new modeling).
- **Dependencies:** W4.4 (suppliers table seeded), E3 (org scoping), E2.
- **Acceptance:** Kraljic places suppliers into the correct quadrant from spend+risk inputs; footprint sums all contracts for a supplier.
- **Effort:** **L.**

### W5.2 — RBAC enforcement + matter-level versioning  (R25)  — ALL

- **User stories:** _As an admin,_ access is enforced per role and per matter; every artifact is versioned and audit-logged for defensibility.
- **Scope in (MVP):** flip **E3** from soft to **hard enforcement** across routers via `require_role`/`require_matter_access`; matter-scoped versioning over key artifacts; complete `AuditLog` coverage. **Out:** field-level redaction.
- **Data model:** **E3** tables (`organizations`, `matter_members`, extended `User.role`); reuse `AuditLog`. No edits to frozen `app/security.py`.
- **API:** dependency added to existing routers (no new business endpoints); `GET /v1/matters/{id}/audit` → `audit_service`.
- **Logic:** rules — deny-by-default per role/matter; audit on every mutation. No LLM.
- **Dependencies:** **E3 (hard)**, E2.
- **Acceptance:** a `procurement` user cannot read another org's playbook or matter; every mutating call writes an `AuditLog` row; enforcement covers all wave routers.
- **Effort:** **L.**
- **Risks:** regressions across many routers (mitigate: soft-mode logging in M1 to find gaps before hard cutover; per-router tests).

### W5.3 — Dual-mode (guided vs power) + "not legal advice" boundary  (R27)  — ALL

- **User stories:** _As a non-lawyer,_ I use guided/plain-language mode; _as a lawyer,_ I switch to power/redline mode. Both log a "not legal advice" acknowledgement.
- **Scope in (MVP):** a `mode` request parameter (`guided|power`) honored by drafting/analysis endpoints (linter-forward in guided; redline/citations in power); logged acknowledgement. **Out:** full per-feature UX divergence.
- **Data model:** new `legal_advice_acknowledgements` (`id`, `user_id`, `feature`, `acknowledged_at`); `User.preferred_mode` additive column.
- **API:** mode param on existing endpoints; `POST /v1/ack/not-legal-advice` → `compliance_service.record_ack`.
- **Logic:** rules — mode toggles which services/prompts run (guided → `linter_service` + plain summary; power → analysis + F5 + citations). Boundary string everywhere (already in `llm_service` SYSTEM_PROMPT).
- **Dependencies:** E3 (role default mode), linter/analysis (exist).
- **Acceptance:** guided mode returns plain-language output + linter; power mode returns redline/citations; first legal-output use records an acknowledgement.
- **Effort:** **M.**

### W5.4 — Closeout / renew-vs-recompete decision support  (R20)  — CM, SSA

- **User stories:** _As a CM,_ at term end I run closeout (lessons-learned) and get renew-vs-recompete decision support feeding back to the SSA.
- **Scope in (MVP):** closeout template + a rules+LLM recommendation (performance history, market signals from W4.2). **Out:** automated recompete launch.
- **Data model:** new `closeouts` (`id`, `matter_id`, `contract_id`, `lessons_json`, `recommendation`, `created_at`).
- **API:** `POST /v1/contracts/{id}/closeout`, `GET /v1/contracts/{id}/renew-recommendation` → `closeout_service`.
- **Logic:** rules (scorecard + key-date inputs) + LLM (recommendation narrative). Closes the relay loop back to SSA (W4).
- **Dependencies:** W1.3 (SLA history), W4.2 (market signal), W5.1 (supplier perf), E2.
- **Acceptance:** closeout captures lessons; recommendation cites performance + market inputs.
- **Effort:** **M.**

---

## 7. Cross-cutting (spans all waves) — R26 sector packs & attribution

- **CCDC / IT-MSA sector packs (R26):** populate `KnowledgeArticle` + `SOWTemplate` + `EvaluationTemplate` + `SLATemplate` rows for **construction (CCDC 2/5B, CCA, ACEC)** and **IT/digital (MSA/SaaS/DPA)**; align `CommodityCategory.unspsc_codes` to **UNSPSC** (§7.4). Pure **data-seeding** via `knowledge_seed`/`clause_seed` patterns — no schema change. Needed by W3.1 (construction/IT RFx) and W2 (sector clause comparison).
- **Bilingual rendering:** the `*_fr` fields exist across models — surface them in exports (E4) where `Jurisdiction.requires_bilingual`.
- **Jurisdiction/source attribution:** every generated artifact carries `source` + `jurisdiction` + (where legal) `JurisprudenceArticle`/`citation_service` references. Enforced in DoD.

---

## 8. Release sequencing view (milestones M1–M9) & critical path

Milestones are dependency-ordered, not calendar-fixed. **Enablers are pulled forward** out of their nominal Wave 5 home (the central tension) and resolved by building **thin slices first, full build-out later.**

| Milestone | Theme | Features | Key enabler work | Can parallelize with |
|---|---|---|---|---|
| **M1** | Foundations slice | — | **E1** (scheduler/notify MVP), **E3** (RBAC enum + `require_role` soft-mode), **E2** (`matters`/`matter_links` tables) | E4 stub, jurisprudence seeding |
| **M2** | CLM runtime | W1.1 alerts, W1.2 compliance currency | consume E1 | E5 design-review kickoff (long lead), R26 IT pack seeding |
| **M3** | CLM runtime cont. | W1.3 SLA monitoring | E1 recurrence | E4 DOCX build, JurisprudenceArticle seeding |
| **M4** | Lawyer power-tools | W2.1 redline round-trip, W2.3 risk memo | **E4** (full), `JurisprudenceArticle` populated | E5 review completes |
| **M5** | Lawyer + tenant playbook | W2.2 playbook | **E5** (post-review) | W3.1 template seeding |
| **M6** | Bidding (draft→evaluate) | W3.1 RFx package, W3.2 eval builder, W3.4 addenda | E4 export, E2 | R26 construction/CCDC pack |
| **M7** | Bidding (score→award→contract) | W3.3 scoring, W3.5 award/debrief, W3.6 bid→contract | **E3 RBAC (evaluators)**, E2 spine | — |
| **M8** | Sourcing front-end | W4.1 method rec, W4.2 market brief, W4.4 supplier discovery, W4.5 intake | E2, benchmark/CanadaBuys ingestion | W4.3 cost-model (data-gated) |
| **M9** | SRM + binding layer | W5.1 supplier master/SRM, W5.2 **RBAC hard-enforce**, W5.3 dual-mode, W5.4 closeout | **E2 Phase-B columns**, **E3 hard cutover**, E5 reused | — |

**Critical path (longest dependency chain):**

```
E1 (M1) → W1.1 (M2) ──┐
E2 (M1) ──────────────┼─→ W3.6 bid→contract (M7) → W1 alert engine sees contract dates
E3 soft (M1) ─────────┘                              │
E4 (M3/M4) → W2.1 (M4) → W3.1 RFx (M6) ──────────────┤
W3.2 (M6) → W3.3 (M7) → W3.5 (M7) ───────────────────┘
W4.4 suppliers (M8) → W5.1 SRM (M9)
E3 soft (M1) ─────────────────────────────────────────→ E3 hard (M9, W5.2)
```

The single longest chain is **E1/E2/E3-soft → bidding workflow (W3) → SRM/RBAC hard (W5)**. The two big de-risking levers:
1. **Pull E1, E2-PhaseA, E3-soft, E4-stub into M1** so no later wave is blocked on greenfield enabler work.
2. **Start two long-lead, code-light tracks immediately and in parallel:** the **E5 PIPEDA design review** (gates W2.2/M5) and **knowledge seeding** (`JurisprudenceArticle` for W2.3; R26 CCDC/IT packs for W3.1; CanadaBuys/benchmark ingestion for W4). These have no code dependency on the waves and otherwise become bottlenecks.

**Parallelization summary:** M2/M3 (CLM) can run alongside M4 (lawyer tools) once E1+E4 land — different services, no shared mutable schema. M8 sourcing is independent of M4–M7 except for the shared E2 spine and can start as soon as ingestion data is ready. The only hard serialization is W3.2→W3.3→W3.5→W3.6 (the evaluation→award→contract chain) and E3-soft→E3-hard.

**Resolution of the "enablers are Wave 5" tension (explicit):** Do **not** wait until Wave 5 to introduce E1/E2/E3. Build their **minimum viable slice in M1** (scheduler that fires; matter tables that link; role dependency in log-only mode), defer their **full build-out** (multi-channel notifications, Phase-B matter columns, hard RBAC enforcement) to their natural Wave-5 milestone (M9). This keeps every wave unblocked while preserving Wave 5 as the place where the binding layer is *completed and enforced*.

---

## 9. Definition of Done & quality gates

Every feature PR must satisfy:

1. **Architecture conformance (CLAUDE.md):** routers thin (HTTP → one service call → HTTP); all business logic in `app/services/`; no DB queries or LLM calls in routers; all new config in `app/config.py` via env vars (no hardcoded keys/URLs/flags).
2. **Migration discipline:** schema delta = **one new Alembic revision** (`alembic revision --autogenerate -m "..."` → manual review of the autogenerated script → `alembic upgrade head`). Never edit a committed migration; never `alembic downgrade` without explicit human approval. Additive/nullable columns only on existing tables. Frozen files (`app/security.py`, `app/middleware/auth.py`, Stripe price IDs, committed `alembic/versions/`) untouched — RBAC composes via a **new** `app/middleware/rbac.py`.
3. **LLM waterfall:** any LLM use goes through the Groq → HF/SaulLM → Claude waterfall wrapper with **per-tier prompt formatting**; deterministic logic (thresholds, weight sums, business-day math, frequency counts, diffs) is **rules-based, never LLM**; outputs carry `source`/`jurisdiction` attribution.
4. **PIPEDA checkpoints:** any feature flagged **[PIPEDA-REVIEW]** (E5/W2.2; W3.3 if storing bid text; cost/market data that quotes contract content) passes a CLAUDE.md rule-6 **design review before merge**. Confirm existing F1/F2/F3 persistence is reconciled with the rule. Notification payloads and matter/supplier records hold **metadata only**, never clause text.
5. **Defensibility / audit (R25):** every mutating endpoint writes an `AuditLog` row; generated legal artifacts carry the **"AI assistance, not legal advice"** boundary and (where the user acts) a logged acknowledgement.
6. **Tests + `/pre-merge-check`:** unit tests for rules logic and migrations; the repo's **`/pre-merge-check`** run clean; CI (GitHub Actions `tests.yml`) green; `PROJECT_STATUS.md` updated. Branch per session conventions (`feature/<letter>-<kebab>`), Conventional Commits, **PRs only — never push to `main`**.
7. **Province-aware:** no generic "Canadian" logic that erases provincial variation; extend `Jurisdiction`/`ProcurementFramework`, default Ontario.

---

## 10. Open questions / decisions needed (for the product owner)

1. **Scheduler topology:** in-process APScheduler (single VPS, simplest) vs an external beat/worker. MVP assumes in-process — confirm we won't horizontally scale the API before W1 ships (affects E1 design).
2. **E5 PIPEDA review timing:** the tenant-playbook store persists customer clause text and gates W2.2. Can the design review start **now** (M1) so it doesn't bottleneck M5? Who owns the review sign-off?
3. **Bid-document storage (W3.3):** MVP stores scores/rationales only, not bid text. Do POs need full bid documents retained in Lexara (CITT defensibility argues yes) — which would trigger a [PIPEDA-REVIEW] and storage design?
4. **Knowledge-seeding ownership & licensing:** who sources/curates CCDC (licensed/copyright), CanLII jurisprudence, CanadaBuys/benchmark data? CCDC documents are **copyrighted** — confirm we model *references/guidance*, not redistributed full text.
5. **RBAC role taxonomy:** confirm the five operating roles (sourcing/procurement/contracts/legal/vendor_mgmt) map cleanly onto the existing three (`admin/procurement/legal`) and onto Stripe plan tiers (free/starter/growth/business) — does role gating interact with billing entitlements?
6. **Matter spine vs existing per-feature sessions:** confirm we standardize on `matters` + `matter_links` (polymorphic) rather than retrofitting `matter_id` everywhere at once — and the lazy backfill approach for F1–F6.
7. **Should-cost data (W4.3):** is there budget/appetite to license commodity/price-index benchmark data? Without it, W4.3 ships as a template calculator only.
8. **Mode default (W5.3):** should `guided` be the default for `procurement/sourcing/contracts` roles and `power` for `legal`, or user-selectable per session?

---

_End of build plan. This document creates no code and modifies no tracked source; it is the design artifact that subsequent feature PRs implement, one Alembic revision and one thin-router/service slice at a time._
