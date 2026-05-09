# LexAra Deployment Guide

LexAra runs on a single VPS using Docker Compose, fronted by Traefik for TLS
and routing. Releases are continuously delivered from GitHub: a push to `main`
triggers `.github/workflows/deploy.yml`, which builds the api image, pushes
it to GHCR, and rolls the running container on the VPS.

---

## Topology

```
                    ┌────────────────── Traefik (TLS, Let's Encrypt) ───┐
                    │                                                   │
  lexara.tech  ─────┼──► frontend  (nginx:alpine, ./website mounted)    │
  api.lexara.tech ──┼──► api       (ghcr.io/mail2vimal11-arch/...)      │
                    │     ├── db    (postgres:16-alpine)                │
                    │     ├── redis (redis:7-alpine)                    │
                    │     └── hf-warmer (curlimages/curl)               │
                    └───────────────────────────────────────────────────┘
```

All services and definitions live in `docker-compose.yml`. The api service is
the only one that ships from GHCR; the rest run upstream images.

---

## Continuous deployment

### Trigger

Any push to `main` (including squash-merged PRs) starts the workflow at
`.github/workflows/deploy.yml`. It can also be run manually via
*Actions → Build and Deploy → Run workflow*.

### Pipeline stages

1. **Build** on a GitHub-hosted runner. The Dockerfile is built with Buildx,
   layer cache is read from / written to GitHub Actions cache, and the image
   is pushed to GHCR with two tags:
   - `ghcr.io/mail2vimal11-arch/lexara-api:latest`
   - `ghcr.io/mail2vimal11-arch/lexara-api:sha-<short-sha>`
2. **Deploy** SSHes to the VPS, fast-forwards the working tree to the new
   `main`, exports `API_TAG=sha-<short-sha>`, and runs
   `docker compose pull api && docker compose up -d api`.
3. **Smoke test** the public endpoint:
   `curl https://api.lexara.tech/status` must return 200. On failure, the
   workflow dumps the last 100 lines of api logs and exits non-zero.

### Required GitHub repository secrets

Already configured on this repo:

| Secret | Purpose |
|---|---|
| `VPS_HOST` | VPS hostname or IP |
| `VPS_USER` | SSH user (must be in the docker group) |
| `VPS_SSH_KEY` | Private key whose public half is in `~/.ssh/authorized_keys` on the VPS |

Image push uses the built-in `GITHUB_TOKEN` — no additional registry secret
is needed because the image is published as a public package on GHCR.

### VPS layout the workflow expects

- `/opt/lexara-api` is a clone of this repository, on branch `main`.
- The deploy SSH user can run `docker compose` without sudo.
- A `.env` file exists at `/opt/lexara-api/.env` with the production secrets
  (see *Required environment variables* below).

---

## Manual deploy (fallback)

The normal path is CI. If GitHub Actions is unavailable, you can roll from
the VPS itself:

```bash
ssh ${VPS_USER}@${VPS_HOST}
cd /opt/lexara-api
./scripts/deploy.sh                 # roll to :latest
./scripts/deploy.sh sha-abc1234     # roll to a specific tag
```

The script does the same `git reset --hard origin/main` + `docker compose
pull && up -d` + smoke test as the workflow.

---

## Rollback

Every successful build leaves a SHA-tagged image on GHCR. To roll back
(typical case: a bad deploy is now serving and you want the previous good
SHA):

```bash
ssh ${VPS_USER}@${VPS_HOST}
cd /opt/lexara-api
./scripts/deploy.sh sha-<previous-good-sha>
```

The previous image isn't deleted until `docker image prune -f` runs at the
end of a subsequent successful deploy, so you typically have at least one
prior image cached locally on the VPS.

---

## Required environment variables (`/opt/lexara-api/.env`)

Variables consumed by `app/config.py`. Names map 1:1 to the `Settings`
fields in that file (case-insensitive).

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | yes | App secret |
| `JWT_SECRET` | yes | JWT signing |
| `JWT_ALGORITHM` | no | Default `HS256` |
| `DATABASE_URL` | yes | `postgresql://user:pass@db:5432/lexaradb` (note `db` is the compose service name) |
| `REDIS_URL` | no | Default `redis://redis:6379/0` |
| `CLAUDE_API_KEY` | yes | Anthropic key |
| `RECEIPTS_API_KEY` | yes | Internal receipt service |
| `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` / `STRIPE_WEBHOOK_SECRET` | yes | Billing |
| `STRIPE_PRICE_STARTER` / `STRIPE_PRICE_GROWTH` / `STRIPE_PRICE_BUSINESS` | yes | Plan price IDs |
| `GROQ_API_KEY` / `GROQ_MODEL` | optional | Enables Groq tier of LLM waterfall |
| `HF_API_TOKEN` / `HF_MODEL_ID` | optional | Enables HF inference + the `hf-warmer` sidecar |
| `USE_GROQ` | no | Default `true`, set `false` to skip Groq |
| `USE_LOCAL_LLM` | no | Default `true`, set `false` to skip local LLM |
| `ALLOWED_ORIGINS` | no | Comma-separated CORS list |
| `POSTGRES_DB_USER` / `POSTGRES_DB_PASSWORD` / `POSTGRES_DB_NAME` | no | Defaults `lexara` / `lexara123` / `lexaradb` (override in production) |

---

## Smoke tests

Endpoints that should always return 200 against a healthy deploy:

```bash
curl -fsS https://api.lexara.tech/health
curl -fsS https://api.lexara.tech/status     # version + uptime + DB check
curl -fsS https://lexara.tech/                # marketing site
```

`/status` (added in PR #8) is the most informative — it returns service
version, process uptime, and the result of a `SELECT 1` against the
database. A `degraded` overall status with `checks.database.status == "error"`
means the new container booted but can't reach Postgres (typically a stale
`DATABASE_URL` or a network misconfiguration).

---

## Operational notes

- **Layer cache.** GHA cache is keyed per branch + workflow. First build on
  a fresh cache takes ~6–8 min (downloads `en_core_web_sm` and the MiniLM
  encoder); subsequent builds with the same `requirements.txt` are ~90 s.
- **Schema migrations.** None today — the app uses
  `Base.metadata.create_all` in the FastAPI lifespan to create missing
  tables idempotently. If you introduce destructive schema changes, add
  Alembic and a migration step in the workflow before `docker compose up`.
- **Backups.** The `postgres_data` volume is not currently backed up.
  Recommended next step: a sidecar that runs `pg_dump` daily and ships the
  archive to off-VPS storage.
- **`hf-warmer`.** Pings the HF Inference endpoint every 10 min so the model
  doesn't go cold. Pinned to `curlimages/curl:8.7.1` and capped at 64 MiB.
