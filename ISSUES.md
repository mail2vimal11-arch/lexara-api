# ISSUES.md
_Authoritative issue tracker. All audit findings logged here. Updated when resolved._
_Sources: Code Audit (2026-05-02) · Frontend Audit (2026-05-02)_

---

## Severity Key
- **P0** — Blocker: crashes, security holes, data loss, or broken core feature. Do not ship.
- **P1** — Must fix before launch: significant functional gap or compliance failure.
- **P2** — Should fix soon: quality, performance, or maintainability.
- **P3** — Nitpick: low-impact polish.

## Status Key
`OPEN` · `IN PROGRESS` · `RESOLVED` · `WONT FIX`

---

## Backend Issues (CA-*)

### P0 — Blockers

| ID | Location | Title | Blocks | Status | Resolution |
|---|---|---|---|---|---|
| CA-001 | `app/database/models.py:63` | `timedelta` not imported — every Analysis INSERT crashes at runtime | CA-018 | RESOLVED | Fixed in `app/models/billing.py` — commit de6b0a2 |
| CA-002 | `app/database/models.py` + `app/models/user.py` | Two competing `User` ORM classes mapped to same `users` table — mapper collision, billing columns inaccessible | CA-003, CA-004, CA-005, CA-009, CA-018 | RESOLVED | Unified model in `app/models/user.py` with all auth + billing columns — commit de6b0a2. Prod migration SQL in commit message. |
| CA-003 | `app/routers/billing.py:55–58,68–69` | `/v1/plans` and `/v1/checkout` are unauthenticated — any caller can create Stripe sessions | CA-004 | RESOLVED | `/v1/checkout` now requires `get_current_user`; user email derived from JWT, not request body |
| CA-004 | `app/routers/billing.py:165–194` | All four Stripe webhook handlers are no-ops — paying users never upgraded in DB | — | RESOLVED | All 4 handlers now perform real DB upserts via `db.query(User)` + `db.commit()`; `db=Depends(get_db)` added to webhook endpoint |
| CA-005 | `app/routers/usage.py:31–42` | `/v1/usage` returns hardcoded fake data — quota enforcement impossible | — | RESOLVED | Real `func.count(Analysis.id)` query for current month; plan limits from `PLANS` dict; remaining quota computed |
| CA-006 | `app/services/llm_service.py:142` | `content` variable may be unbound in `except json.JSONDecodeError` — masks real errors as `UnboundLocalError` | — | RESOLVED | `content = ""` initialised before try block — commit a4edf2f |
| CA-007 | `.github/workflows/tests.yml:43` | `pytest \|\| true` makes CI gate toothless — broken code ships undetected | ALL | RESOLVED | Removed `\|\| true` from pytest step 2026-05-02 |

### P1 — Must Fix Before Launch

| ID | Location | Title | Blocks | Blocked By | Status | Resolution |
|---|---|---|---|---|---|---|
| CA-008 | `app/middleware/auth.py:41–48` | Middleware checks Bearer prefix only — JWT never validated at middleware layer | — | — | OPEN | |
| CA-009 | `app/security.py:50–65` | `get_current_user` is sync; no `is_active` check — suspended accounts can re-authenticate | — | CA-002 | RESOLVED | Made `async def`; added `if not user.is_active: raise HTTPException(403)` |
| CA-010 | `app/services/hf_llm_service.py:130–135` | `asyncio.sleep(60)` holds open DB connection during HF cold-start — can exhaust pool | — | — | OPEN | |
| CA-011 | `app/ingestion/pipeline.py:92–96` | N+1 DB flushes in ingestion loop — degrades linearly with tender volume | — | — | OPEN | |
| CA-012 | `app/routers/procurement_clause_routes.py:66–80` | N+1 SELECT per FAISS result in clause search | — | — | OPEN | |
| CA-013 | `app/services/audit_service.py:34` | Each audit write has its own `db.commit()` — audit failure rolls back business operation | — | — | OPEN | |
| CA-014 | `app/config.py:26–30` | 5 required fields crash app at import if missing; `receipts_api_key` is dead config never used | — | — | OPEN | |
| CA-015 | `tests/conftest.py:180` | `raise_server_exceptions=False` swallows real 500s — test failures are opaque | — | — | OPEN | |

### P2 — Should Fix

| ID | Location | Title | Status | Resolution |
|---|---|---|---|---|
| CA-016 | `llm_service.py` + `groq_llm_service.py` | `key_risks`/`missing_clauses` normalization copy-pasted verbatim — already drifting | OPEN | |
| CA-017 | `app/routers/contracts.py` | `db=Depends(get_db)` injected but never used — wastes connection pool slots | OPEN | |
| CA-018 | `app/database/models.py` | `Analysis`, `APIKey`, `UsageLog`, `BillingEvent` models are dead — never imported, tables never created | RESOLVED | Moved to `app/models/billing.py`, imported in `main.py` and `conftest.py` — commit de6b0a2 |
| CA-019 | `app/routers/billing.py:86` | `success_url + "&session_id=..."` produces invalid URL when no `?` present | RESOLVED | Separator now chosen dynamically: `"&" if "?" in url else "?"` |
| CA-020 | `docker-compose.yml:56–72` | `hf-warmer` uses `latest` floating tag, runs as root, no resource limits | OPEN | |
| CA-021 | `Dockerfile:9` | Sentence Transformers model downloaded at build with no integrity/hash check | OPEN | |
| CA-022 | `app/routers/health.py:15` | Version hardcoded as `"1.0.0"` instead of `settings.version` | OPEN | |
| CA-023 | `app/routers/billing.py:63–65` | `success_url`/`cancel_url` defaults hardcode `lexara.tech` — staging calls hit prod | OPEN | |
| CA-024 | `app/main.py:19–56` | Startup errors swallowed — app starts degraded with no operator alert | OPEN | |

### P3 — Nitpicks

| ID | Location | Title | Status | Resolution |
|---|---|---|---|---|
| CA-025 | `tests/conftest.py:276–292` | `MOCK_EXTRACT_CLAUSES_RESPONSE` uses wrong schema fields vs `ExtractedClause` model | OPEN | |
| CA-026 | `app/routers/auth_routes.py:27` | `register` is `def` (sync) while all other v1 endpoints are `async def` | OPEN | |
| CA-027 | `app/services/groq_llm_service.py:169` | Same unbound `content` pattern as CA-006 | RESOLVED | `content = ""` initialised before try block — commit a4edf2f |
| CA-028 | `app/routers/procurement_clause_routes.py:100` | Use `.is_(True)` instead of `== True # noqa` | OPEN | |
| CA-029 | `app/main.py` | Critical startup failures (DB init) should re-raise, not just log | OPEN | |
| CA-030 | `app/routers/billing.py:63` | Hardcoded prod URLs in billing defaults | OPEN | |

---

## Frontend Issues (FE-*)

### P0 — Blockers

| ID | Location | Title | Blocks | Status | Resolution |
|---|---|---|---|---|---|
| FE-001 | `website/script.js:7`, `procurement.html:341`, `procurement-ai.html:351` | Hardcoded `'Bearer demo-api-key-lexara'` sent on all analysis calls — real JWT never used; unauthenticated users have unlimited quota | — | RESOLVED | Replaced static key with `Bearer ${localStorage.getItem('pai_token') \|\| ''}` in script.js and procurement.html; procurement-ai/intelligence already used authHeaders() 2026-05-02 |
| FE-002 | `website/index.html:11` | Skip link is inside `<head>` not `<body>` — non-functional, WCAG 2.4.1 failure | — | RESOLVED | Moved to first element inside `<body>` 2026-05-02 |

### P1 — Must Fix Before Launch

| ID | Location | Title | Blocked By | Status | Resolution |
|---|---|---|---|---|---|
| FE-003 | `docker-compose.yml` + missing `nginx.conf` | No custom nginx config — `/terms`, `/privacy`, all footer links 404 on default nginx:alpine | — | RESOLVED | Created `website/nginx.conf` with try_files routing for /terms and /privacy; mounted in docker-compose.yml 2026-05-02 |
| FE-004 | `website/styles.css` | `.nav-logo`, `.logo-mark`, `.logo-text`, `.logo-accent` classes missing — procurement page headers render unstyled | — | RESOLVED | Added matching CSS rules at end of styles.css mirroring .brand/.brand-name visual pattern 2026-05-02 |
| FE-005 | `procurement.html:169–186`, `procurement-ai.html:169–193` | No `<label>` elements on auth form inputs — AODA/WCAG 1.3.1 violation contradicts footer compliance claim | — | RESOLVED | Added `<label for="...">` to all auth form inputs in procurement-ai.html and procurement-intelligence.html 2026-05-02 |
| FE-006 | `script.js:6`, `auth.html:139`, `procurement.html:341`, `procurement-ai.html:351`, `procurement-intelligence.html:408` | `API_BASE` hardcoded in 5 separate files — no env substitution, local dev hits prod | FE-001 | RESOLVED | Each file retains single top-level API constant; duplicate GATE_API removed from script.js 2026-05-02 |
| FE-007 | `website/index.html:487–499` | Footer links `/about`, `/blog`, `/security`, `/accessibility` point to non-existent pages — all 404 | FE-003 | RESOLVED | Removed /about, /blog, /security, /accessibility links from footer; replaced with HTML comments 2026-05-02 |
| FE-008 | `docker-compose.yml` | No security headers on frontend container (`X-Frame-Options`, `CSP`, `Referrer-Policy`) | FE-003 | RESOLVED | Security headers added to website/nginx.conf (X-Frame-Options, X-Content-Type-Options, Referrer-Policy, CSP) 2026-05-02 |
| FE-009 | `website/auth.html:196–213` | Auto-login after registration has no error handling on inner fetch — user sees "signing you in…" then nothing | — | RESOLVED | Wrapped auto-login fetch in try/catch; on error shows "Account created! Please sign in manually." and redirects to login tab 2026-05-02 |
| FE-010 | `procurement-ai.html`, `procurement-intelligence.html` | `triggerIngestion()` calls `res.json()` without checking `res.ok` | — | RESOLVED | Added `if (!res.ok) throw new Error(...)` before `.json()` call in both files 2026-05-02 |

### P2 — Should Fix

| ID | Location | Title | Status | Resolution |
|---|---|---|---|---|
| FE-011 | `website/index.html` | No favicon, no Open Graph / Twitter Card meta tags | OPEN | |
| FE-012 | `website/index.html.bak` | Backup file served publicly by nginx — information disclosure | RESOLVED | Deleted website/index.html.bak 2026-05-02 |
| FE-013 | `docker-compose.yml` | No gzip/brotli compression or `Cache-Control` headers in nginx | OPEN | |
| FE-014 | `website/index.html:409–417` | CTA email form is a silent no-op — all submissions discarded, no backend call | OPEN | |
| FE-015 | `procurement*.html` inline `<style>` blocks | Inline styles use raw hex values instead of the CSS token system from `styles.css` | OPEN | |
| FE-016 | `procurement-intelligence.html:683` | Two different constant names for same API base URL in same script block | OPEN | |

### P3 — Nitpicks

| ID | Location | Title | Status | Resolution |
|---|---|---|---|---|
| FE-017 | `procurement.html`, `procurement-ai.html`, `procurement-intelligence.html` | Copyright year says 2025 (should be 2026) | OPEN | |
| FE-018 | `website/script.js` | Dead code: `switchAuthTab` stub, `renderExtractClauses`, `gate-*` listeners, duplicate `GATE_API` | OPEN | |
| FE-019 | `procurement-intelligence.html:140` | Empty `<li></li>` in nav list | OPEN | |
| FE-020 | Procurement pages tab buttons | Emoji in tab button labels not wrapped in `aria-hidden="true"` | OPEN | |
| FE-021 | `website/script.js` `promptEmail()` modal | Modal has no `role="dialog"`, no focus trap | OPEN | |
| FE-022 | Multiple pages | `target="_blank"` links have no "opens in new tab" warning | OPEN | |
