# LexAra UAT — End-to-end smoke against the live deployment

Drives `lexara.tech` and `api.lexara.tech` with Playwright (Chromium),
captures a screenshot per step, and writes a single `.pptx` summarising
pass/fail per case.

## Where it runs

- **CI (default).** `.github/workflows/uat.yml` runs nightly at 03:00 UTC
  and on demand via *Actions → UAT → Run workflow*. The `.pptx` and the
  raw screenshots are attached as workflow artifacts, retained 30 days.
- **Locally.** Useful for iterating on test cases before pushing.

## Run locally

```bash
pip install -r tests/uat/requirements.txt
python -m playwright install --with-deps chromium

# Headed run against the live site (watch the browser drive)
UAT_HEADLESS=0 python tests/uat/run_uat.py

# Headless run against a staging URL
UAT_BASE_URL=https://staging.lexara.tech \
UAT_API_BASE_URL=https://staging-api.lexara.tech \
python tests/uat/run_uat.py
```

The script writes:

```
qa-reports/<UTC-timestamp>/
  Lexara_UAT_<UTC-timestamp>.pptx
  screenshots/
    landing_page.png
    auth_page.png
    ...
```

## Environment variables

| Name | Default | Purpose |
|---|---|---|
| `UAT_BASE_URL` | `https://lexara.tech` | Public site under test |
| `UAT_API_BASE_URL` | `https://api.lexara.tech` | API under test |
| `UAT_OUTPUT_DIR` | `qa-reports/<timestamp>` | Where the report and screenshots go |
| `UAT_HEADLESS` | `1` | Set `0` to watch the browser during local runs |
| `UAT_TEST_USER_EMAIL` | unset | If set, runs the authenticated flow case |
| `UAT_TEST_USER_PASSWORD` | unset | Pair with `UAT_TEST_USER_EMAIL` |

## Cases covered (v1)

API:
- `GET /health` — 200 with `status` field
- `GET /status` — 200 with `service`, `version`, `uptime_seconds`

Frontend (per page: load, assert `<title>`, full-page screenshot):
- `/` — Landing
- `/auth.html` — Sign in
- `/procurement.html` — Procurement Tools
- `/procurement-ai.html` — Procurement AI
- `/procurement-intelligence.html` — Procurement Intelligence
- `/negotiation-arena.html` — Negotiation Arena
- `/privacy.html` — Privacy Policy
- `/terms.html` — Terms of Service

Authenticated flow (skipped unless `UAT_TEST_USER_EMAIL` + `UAT_TEST_USER_PASSWORD` are set):
- Sign in via `/auth.html`, screenshot the post-login landing.

## Adding a case

Append a tuple to `PAGE_CASES` in `run_uat.py` for a simple
load-and-assert-title case. For interactive flows (clicks, form fills),
follow the `run_authenticated_flow` pattern — accept a `Page`, capture
your own screenshots via `_shot(page, name)`, and return one or more
`StepResult` objects.

## Exit codes

- `0` — every case passed (or skipped cleanly).
- `1` — one or more cases failed. The `.pptx` is still written so
  failures are visible in the report.
- `2` — uncaught exception in the driver itself.
