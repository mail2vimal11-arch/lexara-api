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

sleep 6
if curl -fsS --max-time 10 https://api.lexara.tech/status > /dev/null; then
  echo "Deploy of $API_TAG OK"
else
  echo "Smoke test failed — last 100 lines of api logs:"
  docker compose logs --tail=100 api
  exit 1
fi
