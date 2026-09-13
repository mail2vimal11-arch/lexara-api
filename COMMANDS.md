# Lexara — Command Cheat Sheet

Copy-paste commands for the common tasks. Two environments:

- **VPS** = your production server (`/opt/lexara-api`), serves `lexara.tech` + `api.lexara.tech`.
- **Local** = your dev machine (a clone of this repo).

The pipeline auto-deploys on every merge to `main` (tests → build image → SSH to VPS → roll the `api` container). The commands below are for **manual** control and troubleshooting.

---

## 1. Deploy / "build" the latest code on the VPS

> The website (HTML/CSS/JS) is served **live from the `./website` folder** — a `git pull` alone updates it instantly, no build needed. Only the **API** runs as a built Docker image.

**Full manual deploy (API + website), run on the VPS:**
```bash
cd /opt/lexara-api
git fetch origin main
git reset --hard origin/main      # updates code + website files
docker compose pull api           # get the newest API image from GHCR
docker compose up -d api          # recreate the API container (re-reads .env)
docker image prune -f
docker compose ps                 # confirm api is "healthy"
```

**Website-only change (fastest — HTML/JS edits like the login page):**
```bash
cd /opt/lexara-api
git fetch origin main && git reset --hard origin/main
# nginx serves the folder live — nothing to restart.
# If a browser still shows the old page, it's browser cache: hard-refresh
# (Cmd+Shift+R / Ctrl+Shift+R) or open in a private window.
```

**Rebuild the API image locally (only needed for local dev, not prod):**
```bash
cd /opt/lexara-api
docker compose build api
docker compose up -d api
```

---

## 2. Trigger a deploy from GitHub (no SSH)

Merging any PR into `main` auto-deploys. To re-run the last deploy without a new commit, in the repo on GitHub: **Actions → "Build and Deploy" → Run workflow → main**.

---

## 3. Password reset (while email/SMTP is not configured)

The reset link is written to the **API logs** instead of being emailed.

1. In a browser: **https://lexara.tech/auth.html?mode=forgot** → enter your email → submit.
2. On the VPS, grab the link:
```bash
cd /opt/lexara-api
docker compose logs --since 10m api | grep "reset link"
```
3. Open the printed `https://lexara.tech/auth.html?reset_token=...` link within **30 minutes**, set a new password, sign in.

**To enable real reset emails**, add to `/opt/lexara-api/.env` then `docker compose up -d api`:
```bash
SMTP_SERVER=smtp.yourprovider.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-user
SMTP_PASSWORD=your-smtp-pass
```

---

## 4. Logs & health

```bash
cd /opt/lexara-api
docker compose ps                          # container status/health
docker compose logs --tail=100 api         # recent API logs
docker compose logs -f api                 # live tail (Ctrl+C to stop)
docker compose logs --tail=50 web          # nginx (website) logs
curl -s https://api.lexara.tech/status     # is the API up?
curl -s https://api.lexara.tech/health     # detailed health (DB etc.)
```

**Check CORS (the "Load failed" class of bug):**
```bash
curl -si -X OPTIONS https://api.lexara.tech/v1/auth/register \
  -H "Origin: https://lexara.tech" \
  -H "Access-Control-Request-Method: POST" | grep -i access-control
# Expect: access-control-allow-origin: https://lexara.tech
```

---

## 5. Restart / recover

```bash
cd /opt/lexara-api
docker compose restart api        # quick restart (does NOT re-read .env)
docker compose up -d api          # recreate (DOES re-read .env — use after .env edits)
docker compose down && docker compose up -d   # full stack restart
```

> ⚠️ Never run `docker compose down -v` — the `-v` deletes the database volume.

---

## 6. Database

```bash
cd /opt/lexara-api
# open a psql shell (service name is 'db'):
docker compose exec db psql -U lexara -d lexaradb

# quick user check:
docker compose exec db psql -U lexara -d lexaradb -c \
  "SELECT username, email, plan_id, is_active FROM users ORDER BY created_at DESC LIMIT 10;"
```

> Schema is auto-reconciled on startup (missing columns added). No manual `ALTER TABLE` needed.

---

## 7. Local development

```bash
# from a fresh clone:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# run the API locally (needs SECRET_KEY + JWT_SECRET set):
SECRET_KEY=dev JWT_SECRET=dev uvicorn app.main:app --reload --port 8000

# run the website locally (separate terminal):
cd website && python3 -m http.server 8080
# then open http://localhost:8080/auth.html  (API calls go to localhost:8000)

# run the full test suite:
pytest tests/ -q
```

---

## 8. Git workflow

```bash
git checkout main && git pull origin main
git checkout -b feature/my-change      # branch naming: feature/<letter>-<task>
# ... edit ...
git add -A && git commit -m "feat: describe change"
git push -u origin feature/my-change
# open a PR to main on GitHub; merge → auto-deploy.
```
