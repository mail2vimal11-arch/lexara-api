# Lexara API — Pre-Deploy End-to-End QA Report

**Date:** 2026-06-04
**Engineer:** QA automation pass (Claude Code)
**Repo:** `/home/user/lexara-api` · branch `claude/lexara-procurement-roles-WgnTh`
**Scope:** Full pre-deploy quality assessment of the current state — backend install/import/tests/E2E, frontend static site, security smoke, and ISSUES.md spot-check.

---

## 1. Executive Go / No-Go

**Recommendation: CONDITIONAL GO — backend product quality is strong; ship is gated on resolving two non-code-quality items below.**

The backend is in good shape: dependencies install cleanly, the app imports without errors, and the full test suite passes **346 passed / 2 skipped / 0 failed**. An independent E2E probe across all six feature areas confirmed sane behavior, correct auth enforcement, and correct RBAC. The frontend ISSUES.md fixes I spot-checked are genuinely present.

Two items hold back an unconditional GO:

1. **CI/CD deploy gate is bypassable (P1).** Two GitHub workflows both trigger on `push: main`. `tests.yml` gates its deploy on `needs: test`, but `deploy.yml` builds + SSH-deploys with **no test dependency** (`deploy` only `needs: build`). A push to `main` with failing tests will still deploy via `deploy.yml`. This defeats the CA-007 "CI gate" hardening. Must be reconciled before relying on automated deploy. *(Not verifiable live — assessed from workflow YAML only.)*

2. **Documentation/code drift on a security-relevant control (P2, verify intent).** `ISSUES.md` CA-003 states `/v1/checkout` "now requires `get_current_user`." The actual code does **not** require auth on `/v1/checkout` (it is whitelisted in middleware and has no auth dependency), and its own docstring says auth is *"deliberately omitted."* This is a deliberate product decision (public landing-page checkout) — but the issue tracker records the opposite. Confirm the intended posture and fix whichever is wrong. As-is, anyone can create Stripe Checkout sessions unauthenticated (low risk for subscription checkout, but worth an explicit decision).

Neither is a code crash or data-loss blocker, so this is a GO **provided** item 1 is fixed (or manual-deploy discipline is enforced) and item 2 is an accepted, documented decision.

---

## 2. Environment — What Was Executed vs Blocked

| Step | Result | Evidence |
|---|---|---|
| Python version | Python **3.11.15** | `python3 --version` |
| venv | Pre-existing empty `venv/` reused | `venv/bin/python --version` → 3.11.15 |
| `pip install -r requirements.txt` | **SUCCESS (exit 0)** | "Successfully installed … fastapi-0.109.0 … torch-2.12.0 …" — no resolution failures |
| App import (`app.main:app`) | **OK** (78 routes) with a `postgresql://` URL | see §4 |
| Full `pytest tests/` | **346 passed, 2 skipped, 0 failed** in ~39s | see §5 |
| Independent TestClient E2E probe | **All probes returned expected status** | see §6 |
| Live Postgres / Redis | **BLOCKED — not available.** Tests use SQLite in-memory via `conftest.py` monkeypatch; heavy ML libs (faiss/sentence-transformers/spacy) are stubbed. | conftest.py:28-75 |
| Linters / type checks | **NOT CONFIGURED** — no flake8/ruff/mypy config or deps in repo | no config files found |
| Coverage % | **NOT MEASURABLE** — `pytest-cov` not in requirements | requirements.txt |
| Live API/site UAT (lexara.tech) | **BLOCKED / out of scope** — no network UAT performed; existing UAT-* findings reviewed from ISSUES.md | — |

**Install note (requested):** requirements pins core packages tightly but leaves the ML stack (`spacy>=3.7.0`, `sentence-transformers==2.3.1` deps, etc.) to float, so transitive resolution pulled newer majors (transformers 4.57.6, torch 2.12.0, numpy 1.26.4, spacy 3.8.14). Install succeeded but downloaded ~5.5 GB incl. NVIDIA CUDA wheels — slow and heavy for a CPU-only image; see DEP-2 in §9. No `pip` resolution errors surfaced.

---

## 3. Per-Feature / Endpoint Results

Legend: **PASS** = exercised, sane response · **BLOCKED** = infra missing · **NOT-VERIFIABLE** = needs live LLM/external service · evidence is from the independent probe (§6) or the test suite (§5) unless noted.

| Feature / Endpoint | Method | Result | Evidence / Notes |
|---|---|---|---|
| `/health`, `/status`, `/` (root) | GET | **PASS** | 200/200/200 |
| `/v1/plans` (public) | GET | **PASS** | 200; all 4 plans present, free=0, business=-1 (test_e2e) |
| Auth register | POST `/v1/auth/register` | **PASS** | 200; dup → 400 |
| Auth login (JWT) | POST `/v1/auth/login` | **PASS** | 200 + `access_token`; wrong pw → 401 |
| Auth enforcement (no token) | various | **PASS** | 401 on all protected /v1 routes |
| Bad/tampered/lowercase token | GET `/v1/usage` | **PASS** | 401 (middleware JWT validation, CA-008) |
| **Contracts** summary / risk-score / key-risks / missing-clauses / extract-clauses | POST | **PASS (mocked LLM)** / **NOT-VERIFIABLE (live LLM)** | All 5 pass with mocked `analyze_with_claude` (test_e2e). With no LLM key the Claude tier raises → 500 by design; requires external LLM, not exercised live. Validation (100/50,000 char) → 400 verified. |
| Upload | POST `/v1/upload` | **PASS** | txt extract OK; empty → 422; no-auth → 401 (test_e2e) |
| **SOW Workbench** commodities/jurisdictions (public) | GET | **PASS** | 200/200 |
| Workbench session/guidance/draft-section/export/sla-template | POST/GET | **PASS** | sla-template → 422 without required `commodity_category_code` (correct validation, not a bug); session lifecycle covered in test_workbench_extract |
| **Portfolio** obligations CRUD + cascade-check | GET/POST/PATCH/DELETE | **PASS** | `/v1/portfolio/contracts` 200 authed / 401 no-auth; CRUD + cascade in test_portfolio_routes (passing) |
| Obligation temporal analyze/timeline | POST/GET | **PASS** | test_obligation_temporal_routes (passing) |
| Dark-obligation detect/catalog | POST/GET | **PASS** | `/v1/dark-obligations/catalog` 200 authed / 401 no-auth; test_dark_obligations passing |
| Negotiation start/propose/respond | POST | **PASS** | test_negotiation passing; routes registered (module present) |
| Bid stress-test | POST `/v1/bid-comparison/stress-test` | **PASS** | 401 no-auth; test_bid_comparison passing |
| **Procurement** lint / citations / clauses | POST | **PASS** | lint 200 (detects legalese), citations 200 (detects statutes), clause search 200 |
| Procurement clause AI analyze/search/library | POST/GET | **PASS** | 200 (FAISS stubbed in tests) |
| Ingestion run / tenders | POST/GET | **PASS** | tenders 200 (procurement role); run → **403** for procurement role (admin-only RBAC correct) |
| **Billing** plans/checkout/webhook | GET/POST | **PASS / see CA-003 caveat** | plans 200; checkout free→400, bad email→422, unknown plan→400; **checkout requires no auth** (see §1.2); webhook bad-sig→400, happy-path handlers covered in test_billing_stripe (passing) |
| Usage | GET `/v1/usage` | **PASS** | 200; real AuditLog-based counts (CA-005). Quota derived from **role**, not `plan_id` — see BUG-3 |

No endpoint returned an unexpected 500 in the probe. All analysis-mode 500s are by-design fallback failures when no LLM credential is present (mocked in tests).

---

## 4. App Import / Static Health

- `import app.main` **fails under a `sqlite://` URL** because `app/database/session.py:8-14` hardcodes `pool_size=10, max_overflow=20` (invalid for SQLite). This is **expected**: production uses Postgres, and `conftest.py` monkeypatches `create_engine` to strip those kwargs for the test DB. Under a `postgresql://` URL the app imports cleanly (engine is lazy; no eager connect at import):

  ```
  IMPORT OK — title: LexAra API
  total routes: 78
  ```
- Non-fatal warning at import: `spaCy model not found. Sentence extraction will fall back to regex.` — acceptable; regex fallback is intentional.
- `config.py` requires `secret_key` and `jwt_secret` (no defaults) and will `ValidationError` at import if unset — matches the documented PO-001/PO-008 hardening. Stripe/Claude keys are `Optional`, so the app boots without them.

---

## 5. Backend Test Suite

Command: `venv/bin/python -m pytest tests/ -q -p no:cacheprovider --tb=short`

```
........................................................................ [ 20%]
........................................................................ [ 41%]
........................................................................ [ 62%]
........................................................................ [ 82%]
...ss.......................................................             [100%]
346 passed, 2 skipped, 3 warnings in 39.09s
```

- **0 failures, 0 errors.** Matches the commit-message claim "346 passed".
- **2 skipped** (intentional): `test_performance_load.py:352` and `:374` — live API benchmarks gated behind `LEXARA_LIVE_TEST=1`.
- **3 warnings** (all benign): Pydantic v2 class-based `config` deprecation (config.py:75 `class Config`), `passlib`/`crypt` deprecation (Python 3.13), `pypdf`/ARC4 cryptography deprecation.
- **Slowest tests** (all bcrypt/auth-bound, normal): `test_login_median_latency_under_500ms` 2.69s, `test_20_concurrent_login_requests_no_500` 1.41s, security-tenancy isolation tests ~1.0–1.1s each. No flaky/fragile tests observed in a clean run.
- **Coverage:** not measured (pytest-cov absent). The 21 test files cover billing, AI reliability, security/tenancy, performance, e2e, frontend-e2e, and each feature module — broad surface, but a numeric figure could not be produced in this environment.

---

## 6. Independent E2E Probe (TestClient)

A standalone script booted the real `app.main:app` under the conftest SQLite harness and exercised endpoints directly. Verbatim output (noise filtered):

```
GET /health                                -> 200
GET /status                                -> 200
GET / (root)                               -> 200
GET /v1/plans (public)                     -> 200
GET /v1/workbench/commodities (public)     -> 200
GET /v1/workbench/jurisdictions (public)   -> 200
NOAUTH /v1/usage                           -> 401
NOAUTH /v1/summary                         -> 401
NOAUTH /v1/upload                          -> 401
NOAUTH /v1/procurement/lint                -> 401
NOAUTH /v1/portfolio/contracts             -> 401
NOAUTH /v1/dark-obligations/catalog        -> 401
NOAUTH /v1/bid-comparison/stress-test      -> 401
register                                   -> 200
login                                      -> 200
BADTOKEN /v1/usage                         -> 401
lowercase bearer /v1/usage                 -> 401
GET /v1/usage (authed)                     -> 200
GET /v1/plans (authed)                     -> 200
POST /v1/checkout free (auth)              -> 400
POST /v1/checkout free (NO auth)           -> 400     <-- checkout reachable WITHOUT auth
POST /v1/checkout bad email 422            -> 422
POST /v1/summary short 400                 -> 400
POST /v1/procurement/lint                  -> 200
POST /v1/procurement/citations             -> 200
POST /v1/procurement/clauses               -> 200
GET /v1/procurement/clauses/library        -> 200
GET /v1/procurement/ingestion/tenders      -> 200
POST /v1/procurement/ingestion/run (proc=403) -> 403
GET /v1/portfolio/contracts (authed)       -> 200
GET /v1/dark-obligations/catalog (authed)  -> 200
GET /v1/workbench/sla-template (authed)    -> 422  (missing required query param — correct)
POST /v1/webhooks/stripe bad sig 400       -> 400
```

---

## 7. Frontend (`website/`) Findings

Static inventory: `index.html`, `auth.html`, `procurement.html`, `procurement-ai.html`, `procurement-intelligence.html`, `negotiation-arena.html`, `privacy.html`, `terms.html`, `script.js`, `styles.css`, `nginx.conf`.

**ISSUES.md FE-* RESOLVED items — re-verified present:**

| Item | Claim | Verified |
|---|---|---|
| FE-001 | Hardcoded `Bearer demo-api-key` removed | **CONFIRMED** — no `demo-api-key` anywhere; `getAuthHeader()` uses `localStorage.getItem('pai_token')` (script.js:8-11) |
| FE-002 | Skip link moved into `<body>` | **CONFIRMED** — `index.html:58` skip-link is first element after `<body>` (line 56) |
| FE-003 | nginx.conf with /terms /privacy routing | **CONFIRMED** — `nginx.conf` has `try_files /terms.html` / `/privacy.html`; mounted in docker-compose.yml:7 |
| FE-004 | `.nav-logo/.logo-*` CSS classes | **CONFIRMED** — 4 matching rules in styles.css |
| FE-005 | `<label>` on auth inputs | **CONFIRMED** — 6 labels each in procurement-ai.html / procurement-intelligence.html (procurement.html has only a search box, no auth form — scope correct) |
| FE-007 | Dead footer links removed | **CONFIRMED** — no `/about /blog /security /accessibility` hrefs remain |
| FE-008 | Security headers in nginx | **CONFIRMED** — X-Frame-Options, X-Content-Type-Options, Referrer-Policy, CSP all present |
| FE-009 | Auto-login error handling | **CONFIRMED** — auth.html:212 "Account created! Please sign in manually." in catch |
| FE-010 | `res.ok` checks before `.json()` | **CONFIRMED** — `if (!res.ok) throw` incl. triggerIngestion (procurement-ai.html:609) |
| FE-012 | `index.html.bak` deleted | **CONFIRMED** — no `*.bak` files |
| FE-013 | gzip + Cache-Control | **CONFIRMED** — `gzip on` in nginx.conf |
| FE-017 | Copyright year 2026 | **CONFIRMED** — © 2026 in all three procurement pages |
| FE-021 | Modal `role="dialog"`/aria | **CONFIRMED** — script.js:398 |

**Frontend ↔ backend route alignment:** All frontend `fetch` targets map to real backend routes — `/v1/{summary,risk-score,...}`, `/v1/upload`, `/v1/checkout`, `/v1/negotiation/start`, `/v1/procurement/{lint,citations,clauses}`, `/v1/procurement/clauses/{library,search,analyze}`, `/v1/procurement/compare/clauses`, `/v1/procurement/ingestion/{run,tenders}`, `/v1/auth/{login,register}`. No orphan calls.

**Remaining frontend observations (not blockers):**

- **FE-006 (partially still true):** `API_BASE`/`API` is hardcoded to `https://api.lexara.tech/v1` in 5 files (`script.js:6`, `auth.html:139`, `procurement.html:341`, `procurement-ai.html:369`, `procurement-intelligence.html:426`). ISSUES marks this RESOLVED on the narrow grounds of "single top-level constant per file," but the value still hardcodes prod — local/staging dev hits prod. Only `negotiation-arena.html:526-527` does a `localhost` check. **Inconsistent and a real dev-env footgun (P3).**
- **No `alt` attributes needed** — landing/procurement pages use inline SVG, no `<img>` tags.
- `WEBSITE_DESIGN_REVIEW.md` describes a blue/white palette, but the live `styles.css` uses a dark/gold token system (`--gold`, `--surface`, `--critical`). The design-review doc is **stale** vs the shipped design (doc hygiene, not a defect).

---

## 8. Security Smoke (non-destructive, controls verified in code + probe)

| Control | Status | Evidence |
|---|---|---|
| Auth enforced on protected /v1 routes | **PASS** | 401 on every protected route without token (§6) |
| JWT validated at middleware (CA-008) | **PASS** | `middleware/auth.py:74-87` `jwt.decode`; bad/lowercase tokens → 401 (§6) |
| Expired-token handling | **PASS (code)** | `ExpiredSignatureError` caught before `JWTError` in both middleware and `security.decode_token` |
| `is_active` suspension gate (CA-009) | **PASS (code)** | `security.py:80-81` raises 403 for inactive users; `get_current_user` is `async` |
| RBAC (admin-only ingestion) | **PASS** | procurement role → 403 on `/v1/procurement/ingestion/run` (§6) |
| Webhook signature verification (CA-004) | **PASS** | bad signature → 400 (§6); `stripe.Webhook.construct_event` enforced |
| `/v1/checkout` auth (CA-003/CA-004) | **MISMATCH** | Code does **not** require auth (intentional per docstring); ISSUES.md says it does. See §1.2 — confirm posture. |
| Secret leakage in repo/static site | **PASS** | No `sk_live`/`sk-ant-`/`gsk_live`/private keys in `app/` or `website/`. `.env.example` uses placeholders. Stripe **price** IDs in config.py are non-secret identifiers. `.dockerignore` excludes `.env`. |
| Rate limiting (slowapi) | **NOT-VERIFIABLE** | slowapi installed/configured but enforcement not exercised here (matches known tech-debt note in CLAUDE.md) |

---

## 9. Prioritized Defect List

### P1
- **CI-1 — Deploy bypasses test gate.** `.github/workflows/deploy.yml` deploys on `push: main` with `deploy: needs: build` (no `needs: test`), running in parallel with the gated `tests.yml`. Failing tests will still deploy via `deploy.yml`. Also the two paths conflict (GHCR prebuilt image + `git reset --hard` vs. local `git pull` + `docker compose build`). **Reconcile into one gated pipeline before trusting auto-deploy.** *(Workflow-YAML analysis; not run live.)*
- **DEP-1 — Known-vulnerable pinned dependencies (matches the "dependabot 32 vulns" note).** Several pins are versions with well-known public CVEs: `python-jose==3.3.0` (CVE-2024-33663 algorithm confusion, CVE-2024-33664), `python-multipart==0.0.6` (CVE-2024-24762 / 53981 ReDoS), `starlette 0.35.1` (CVE-2024-47874 multipart DoS), `fastapi==0.109.0`, `pypdf==4.1.0`. Plan an upgrade + `pip-audit` in CI. *(Flagged from public advisories; no live CVE scan run in this env.)*

### P2
- **BUG-3 — Usage quota decoupled from billing plan.** `usage.py` derives the analysis limit from `current_user.role` (`_ROLE_PLAN`, usage.py:28-33), but Stripe webhooks write `user.plan_id` (billing.py:197,222,241). A user who upgrades via Stripe gets a new `plan_id` but **no quota change** unless their `role` also changes. Quota enforcement and paid plan are inconsistent. (`app/routers/usage.py:66`, `app/routers/billing.py:182-243`)
- **DOC-2 — ISSUES.md CA-003 contradicts code** (`/v1/checkout` auth). Tracker says auth required; code intentionally public. Reconcile record with intent. (`ISSUES.md:26`, `app/routers/billing.py:71-119`, `app/middleware/auth.py:36`)
- **ENV-1 — No linter/type-check/coverage tooling.** No ruff/flake8/mypy/pytest-cov configured, so the "70% overall / 90% critical-path" coverage target in `docs/TEST_PLAN.md` cannot be measured or enforced in CI.
- **DEP-2 — ML stack floats + heavy CUDA install.** `spacy>=3.7.0` (loose) pulled spaCy 3.8.14 / transformers 4.57.6 / torch 2.12.0 with ~5.5 GB of NVIDIA CUDA wheels on a CPU-only target. Pin the ML stack and use CPU-only torch wheels to make builds reproducible and lean. (`requirements.txt`)

### P3
- **FE-006-residual — Hardcoded prod `API_BASE` in 5 frontend files** (no env substitution); only `negotiation-arena.html` handles localhost. Local/staging dev hits prod. ISSUES marks RESOLVED on narrow grounds.
- **STYLE-1 — Pydantic v2 deprecation:** `config.py:75` uses class-based `class Config`; migrate to `model_config = SettingsConfigDict(...)` to silence the warning and future-proof for Pydantic v3.
- **DOC-3 — `WEBSITE_DESIGN_REVIEW.md` stale** (blue palette vs shipped dark/gold theme); `README.md` still references `lexrisk.com`, `sk_live_abc123`, FastAPI.com deploy, and a `lexrisk-api` repo name that no longer match the product.

---

## 10. "Not Verifiable in This Environment" Caveats

- **No live Postgres/Redis** — all DB tests ran on SQLite in-memory with monkeypatched engine kwargs; production pool behavior (`pool_size=10, max_overflow=20`, `pool_pre_ping`) was not exercised.
- **No live LLM** — Groq/HF/Claude tiers were mocked. The waterfall fall-through logic, prompt formatting per tier, and real model output quality were not exercised against live providers (UAT-003..007 in ISSUES.md cover this against the live deploy, not re-run here).
- **Heavy ML libs stubbed** (faiss, sentence-transformers, spacy) in the test/probe harness — real FAISS search latency/quality and spaCy extraction were not measured. spaCy model is not installed (regex fallback active).
- **No live network UAT** against lexara.tech / api.lexara.tech — frontend findings are from static inspection; runtime browser console errors were not captured.
- **CI/CD findings are from workflow YAML inspection only** — GitHub Actions runs were not triggered.
- **Dependency CVEs flagged from public advisory knowledge**, not a live `pip-audit`/Snyk scan (tooling not present).
- **Coverage %, linting, type-checking** — not measurable (tooling absent).
- **Rate limiting (slowapi)** enforcement not exercised.

---

## Appendix — Commands Executed

```
python3 --version                              # 3.11.15
venv/bin/pip install -r requirements.txt       # exit 0, ~5.5GB, no resolution errors
venv/bin/python -c "import app.main; ..."       # OK with postgresql:// URL, 78 routes
venv/bin/python -m pytest tests/ -q --tb=short  # 346 passed, 2 skipped, 0 failed
venv/bin/python -m pytest tests/ --durations=8 -rs
venv/bin/python /tmp/e2e_probe.py               # independent TestClient probe (§6)
```

No tracked source files were modified. Working tree clean (`git status --short` empty). Only this report was added.
