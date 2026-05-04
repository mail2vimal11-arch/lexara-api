# Lexara — Pre-Merge QA Report (2026-04-28)

**Branch under review:** `claude/condescending-chebyshev-203a38`
(HEAD `94b614d` — identical to current worktree branch `claude/vigilant-gates-8d23e1`)
**Target:** `main`
**QA Lead:** Claude (Opus 4.7)
**Scope:** Feature 2 (SOW Workbench) + Feature 6 (Clause Negotiation Simulator) + regression on existing surface

---

## Executive summary

| Area | Result |
|---|---|
| Total checks executed | **23** |
| PASS | 18 |
| FAIL | 4 |
| SKIP | 1 |
| Existing pytest suite | **244 passed, 2 skipped, 0 failed** (11.24s) |
| Static analysis (py_compile) | **PASS** — all `app/*.py`, `app/**/*.py` compile |
| New-feature test coverage | **0 tests** for Feature 2 and Feature 6 |
| **Merge recommendation** | **🔴 BLOCK** |

**Why BLOCK:** A single P0 routing bug renders all eleven Feature 6 endpoints unreachable from the just-shipped `negotiation-arena.html` frontend, and breaks the multi-party invite flow regardless of UI. The bug is a one-line fix; once corrected and a smoke test added, the branch is otherwise mergeable.

There is no `OPEN_BUGS.md` / `docs/OPEN_BUGS.md` file in the repo.

---

## Feature completion status

### Feature 2 — SOW Workbench

| Sub-area | Status |
|---|---|
| Router `app/routers/workbench_routes.py` | ✅ Present, 11 endpoints |
| Service `app/services/workbench_service.py` | ✅ Present |
| Models `commodity.py`, `jurisdiction.py`, `knowledge.py` | ✅ All present |
| Public-route auth exemptions (`/commodities`, `/jurisdictions`) | ✅ Wired in `APIKeyMiddleware.UNPROTECTED_ROUTES` |
| Knowledge-DB seed loader | ❌ **Module `app/services/knowledge_seed.py` is missing** — referenced at [main.py:56](app/main.py:56) inside a `try/except ImportError` that silently downgrades to a `WARNING` |
| Tests for Feature 2 | ❌ **None** (0 tests reference `/v1/workbench/*` or `workbench_routes`) |

**Effective state:** the schema, models, routers and auth wiring all load cleanly, but on a fresh DB the public catalogue endpoints `/v1/workbench/commodities` and `/v1/workbench/jurisdictions` will return empty arrays and `KnowledgeArticle` will be empty, so guidance / template lookups will fall through to the hard-coded `_default_template_dict` path. Functional but degraded.

### Feature 6 — Clause Negotiation Simulator

| Sub-area | Status |
|---|---|
| Router `app/routers/negotiation_routes.py` | ✅ Present (1500+ LoC, 11 routes) |
| Services `negotiation_ai.py`, `batna_engine.py`, `scenario_simulator.py` | ✅ All present |
| Models `app/models/negotiation.py` | ✅ Present, 4 tables |
| Frontend `website/negotiation-arena.html` | ✅ Present |
| Route registration | ❌ **P0** — duplicated `/v1/negotiation` prefix produces `/v1/negotiation/v1/negotiation/...` |
| Auth exemption for `/join/{token}` | ❌ **P0** — middleware prefix `"/v1/negotiation/join/"` does not match served path |
| Tests for Feature 6 | ❌ **None** (0 tests reference `/v1/negotiation/*`) |

---

## P0 blockers (must fix before merge)

### P0-1 — Negotiation routes are mounted under a duplicated prefix

**Severity:** Blocker — every Feature 6 endpoint is unreachable at the URL the frontend calls.

**Evidence (live route table from `app.routes` after startup):**

```
POST  /v1/negotiation/v1/negotiation/start
GET   /v1/negotiation/v1/negotiation/{session_id}
POST  /v1/negotiation/v1/negotiation/{session_id}/propose
POST  /v1/negotiation/v1/negotiation/{session_id}/respond
POST  /v1/negotiation/v1/negotiation/{session_id}/trade
GET   /v1/negotiation/v1/negotiation/{session_id}/batna
POST  /v1/negotiation/v1/negotiation/{session_id}/scenario
GET   /v1/negotiation/v1/negotiation/{session_id}/ledger
POST  /v1/negotiation/v1/negotiation/{session_id}/invite
POST  /v1/negotiation/v1/negotiation/join/{token}
POST  /v1/negotiation/v1/negotiation/{session_id}/export
```

**Root cause:**
- [app/routers/negotiation_routes.py:39](app/routers/negotiation_routes.py:39) sets `router = APIRouter(prefix="/v1/negotiation", ...)`
- [app/main.py:123](app/main.py:123) then includes it with `prefix="/v1/negotiation"`

Every other router in `app/routers/` uses a relative prefix (e.g. `/auth`, `/clauses`, `/compare`, `/ingestion`) and lets `main.py` add the `/v1[/procurement]` parent — `negotiation_routes.py` is the outlier.

**Frontend impact:** [website/negotiation-arena.html:526–528](website/negotiation-arena.html:526) sets `API_BASE = "http://localhost:8000/v1"` and then calls `apiPost('/negotiation/${sessionId}/propose')` etc., so every fetch resolves to `/v1/negotiation/{id}/propose` — which **404s** against the actual served path.

**Fix:** drop `prefix="/v1/negotiation"` from the `APIRouter()` constructor (line 39), keeping only the `prefix="/v1/negotiation"` in `main.py`. One-line change.

### P0-2 — `/v1/negotiation/join/{token}` is no longer publicly reachable

**Severity:** Blocker for the multi-party flow (opposing counsel cannot accept an invite link).

**Root cause:** A direct consequence of P0-1. [app/middleware/auth.py:30–32](app/middleware/auth.py:30) declares
```
UNPROTECTED_PREFIXES = ("/v1/negotiation/join/",)
```
but the actual served path is `/v1/negotiation/v1/negotiation/join/{token}`, so the middleware rejects the un-authenticated invitee with `401 Authorization header missing or malformed`.

**Fix:** resolved automatically once P0-1 is fixed (the public path becomes `/v1/negotiation/join/{token}` and the prefix matches). After the fix, add a regression test that hits `/v1/negotiation/join/<bogus>` without a Bearer header and asserts the response is **not** 401 (it should reach the route and 404/400 there).

---

## P1 issues (fix before next minor release)

### P1-1 — Zero test coverage for Feature 2 and Feature 6

`grep -rln "v1/workbench\|workbench_routes" tests/` → 0 hits.
`grep -rln "v1/negotiation\|negotiation_routes" tests/` → 0 hits.

A ~1500-LoC Feature 6 router and an 11-endpoint Feature 2 router shipped without a single test — which is precisely why P0-1 escaped the suite. At minimum, add:

- `test_workbench_e2e.py` — `GET /commodities` (public, 200), `GET /jurisdictions` (public, 200), `POST /session` (auth required → 401 without token, 201 with token).
- `test_negotiation_e2e.py` — `POST /v1/negotiation/start`, then `GET /v1/negotiation/{id}`. Doubles as a permanent guard against the prefix bug.

### P1-2 — `app/services/knowledge_seed.py` does not exist

[app/main.py:55–61](app/main.py:55) references it under `try/except ImportError`, so the missing module is silently swallowed at startup with `WARNING knowledge_seed module not yet available — skipping`. Net effect on a fresh DB:

- `Jurisdiction`, `CommoditySector`, `CommodityCategory` tables stay empty → public catalogue endpoints return `[]`.
- `KnowledgeArticle` table stays empty → `workbench_service.get_top_articles` returns nothing → guidance/draft-section endpoints have no reference material.

Either ship the seeder or change the log line to `INFO` and document the manual seeding path. The release notes for commit `498e051` ("Feature 2 knowledge DB schema + test suite + auth fixes") imply the seeder was intended to ship.

---

## P2 / P3 issues (post-merge)

### P2-1 — `hf_llm_service` retries on 503 but not on 429
[app/services/hf_llm_service.py:129–138](app/services/hf_llm_service.py:129) handles HuggingFace's "model loading" 503 with a single retry, but a **429 Too Many Requests** drops straight into the generic `response.status_code != 200` branch and re-raises, so the waterfall jumps to Claude immediately. Add a 429 retry with `Retry-After` honoured (or jittered backoff) before falling through.

### P2-2 — Pydantic v1-style `class Config` in `app/config.py`
Pytest emits `PydanticDeprecatedSince20` for [app/config.py:68](app/config.py:68). Migrate to `model_config = SettingsConfigDict(...)` ahead of Pydantic v3.

### P3-1 — `pip check` reports unrelated noise
Supabase/postgrest/realtime/storage3 conflicts surface in `pip check` because the user's global env has them, but **none are in `requirements.txt`** — Lexara does not depend on them. Recommend adding a CI step that uses a clean venv built only from `requirements.txt` so this noise is filtered out.

### P3-2 — `grpcio 1.80.0 is not supported on this platform`
Same root cause as P3-1 — global env contamination, not a Lexara dep.

---

## All findings (by module)

```
[main.py] — Imports resolve
Status: PASS
Finding: All 14 router imports resolve; lifespan startup wraps each seeder in try/except.

[main.py] — Router registrations match files
Status: PASS
Finding: 12 routers referenced, all 12 files present in app/routers/.

[main.py] — Negotiation prefix duplication
Status: FAIL (P0-1)
Finding: prefix on router (line 39) and include_router (line 123) compose to /v1/negotiation/v1/negotiation/*.

[config.py] — Settings load
Status: PASS
Finding: Required keys load from env or .env; pydantic v1-style Config (P2-2).

[middleware/auth.py] — Public route exemptions
Status: PASS (workbench), FAIL (negotiation/join — P0-2)
Finding: UNPROTECTED_PREFIXES does not match the duplicated negotiation path; resolves on P0-1 fix.

[routers/workbench_routes.py] — Imports + compiles
Status: PASS

[routers/negotiation_routes.py] — Imports + compiles
Status: PASS (compile), FAIL (mount — P0-1)

[services/workbench_service.py] — Imports + compiles
Status: PASS

[services/negotiation_ai.py, batna_engine.py, scenario_simulator.py] — Imports + compile
Status: PASS

[services/llm_service.py] — Waterfall chain
Status: PASS
Finding: Tier 1 Groq (settings.use_groq + groq_api_key) → Tier 2 HF SaulLM (use_local_llm + hf_api_token + hf_model_id) → Tier 3 Claude (claude-haiku-4-5-20251001) all wired.

[services/groq_llm_service.py] — Imports
Status: PASS
Finding: Uses httpx directly (no `groq` SDK dependency required).

[services/hf_llm_service.py] — Retry logic
Status: PASS (503), SKIP (429)
Finding: 503 model-loading retry present; no 429 retry (P2-1).

[services/knowledge_seed.py] — Module presence
Status: FAIL (P1-2)
Finding: Referenced in main.py:56 but file does not exist; ImportError silently swallowed.

[models/commodity.py, jurisdiction.py, knowledge.py, negotiation.py] — Schema
Status: PASS

[website/negotiation-arena.html] — Frontend present
Status: PASS (file ships) / FAIL (target endpoints — P0-1)

[tests/] — Existing suite
Status: PASS
Finding: 244 passed, 2 skipped, 11.24s. No regressions introduced by this branch.

[tests/] — Coverage of new features
Status: FAIL (P1-1)
Finding: 0 tests for Feature 2 or Feature 6.

[requirements.txt] — Core deps pinned
Status: PASS
Finding: fastapi==0.109.0, pydantic==2.5.0, sqlalchemy==2.0.23, httpx==0.25.0, anthropic==0.18.1.

[pip check] — Environment
Status: PASS for Lexara deps (SKIP for Supabase noise — P3-1)
```

---

## Merge gate

| Gate | Required to merge |
|---|---|
| Fix P0-1 (drop duplicate `/v1/negotiation` prefix in `app/routers/negotiation_routes.py:39`) | ✅ **Required** |
| Verify P0-2 resolves automatically post-fix | ✅ **Required** |
| Add at least one smoke test against `/v1/negotiation/start` and `/v1/workbench/commodities` to lock the routing in (P1-1) | ✅ **Required** |
| Ship `knowledge_seed.py` or downgrade the log line and document manual seeding (P1-2) | 🟡 Strongly recommended |
| P2 / P3 items | ⏭ Track post-merge |

Once the two P0 lines are fixed and one smoke test added, this branch is **APPROVE**. Until then: **🔴 BLOCK**.
