#!/usr/bin/env bash
#
# Manual deploy fallback. The normal path is the GitHub Actions workflow at
# .github/workflows/deploy.yml — this script is only for cases where CI is
# unavailable and you need to roll the api service from the VPS itself.
#
# Usage (run on the VPS, from /opt/lexara-api):
#   ./scripts/deploy.sh                 # roll to :latest
#   ./scripts/deploy.sh sha-abc1234     # roll to a specific tagged image
#
set -euo pipefail

cd "$(dirname "$0")/.."

TAG="${1:-latest}"
export API_TAG="$TAG"

echo "Rolling api to $API_TAG"
git fetch --quiet origin main
git reset --hard origin/main

docker compose pull api
docker compose up -d api
docker image prune -f

# Wait for the new container to become healthy. The HEALTHCHECK in the
# Dockerfile probes /status; we poll docker for its result rather than
# guessing a sleep duration. Times out after ~150s (10s * 15 attempts) to
# cover FAISS bootstrap + clause seed on a cold start.
echo "Waiting for api to become healthy..."
for i in $(seq 1 15); do
  state=$(docker inspect --format '{{.State.Health.Status}}' lexara-api-api-1 2>/dev/null || echo "unknown")
  if [ "$state" = "healthy" ]; then
    echo "api is healthy after ${i} attempts"
    break
  fi
  if [ "$i" -eq 15 ]; then
    echo "api never became healthy (last state: $state) — last 100 lines of logs:"
    docker compose logs --tail=100 api
    exit 1
  fi
  sleep 10
done

# End-to-end check through Traefik / TLS.
if curl -fsS --max-time 10 https://api.lexara.tech/status > /dev/null; then
  echo "Deploy of $API_TAG OK"
else
  echo "Container is healthy but public endpoint failed — Traefik routing issue?"
  docker compose logs --tail=50 api
  exit 1
fi
