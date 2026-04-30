#!/usr/bin/env bash
# Pull latest origin/<branch> and rebuild the api container on this VPS.
# Idempotent: exits 0 with no-op if HEAD already matches origin.
#
# Env overrides:
#   LEXARA_REPO_DIR    repo path on the VPS (default: /opt/lexara-api)
#   LEXARA_BRANCH      branch to deploy     (default: main)
#   LEXARA_HEALTH_URL  post-deploy probe    (default: https://api.lexara.tech/status)
set -euo pipefail

REPO_DIR="${LEXARA_REPO_DIR:-/opt/lexara-api}"
BRANCH="${LEXARA_BRANCH:-main}"
HEALTH_URL="${LEXARA_HEALTH_URL:-https://api.lexara.tech/status}"

cd "$REPO_DIR"

echo "==> Fetching origin/${BRANCH}"
git fetch --quiet origin "$BRANCH"

LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git rev-parse "origin/${BRANCH}")

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  echo "==> Already at ${LOCAL_SHA:0:7} — nothing to deploy."
  exit 0
fi

echo "==> ${LOCAL_SHA:0:7} -> ${REMOTE_SHA:0:7}"
git pull --ff-only origin "$BRANCH"

echo "==> Rebuilding and restarting api"
docker compose up -d --build api

echo "==> Probing ${HEALTH_URL}"
for _ in $(seq 1 45); do
  if curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null; then
    echo "==> Healthy. Deployed $(git rev-parse --short HEAD)"
    exit 0
  fi
  sleep 2
done

echo "!! Health check failed after 90s. Run: docker compose logs --tail=200 api" >&2
exit 1
