#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8080}"

echo "API_URL=$API_URL"
curl -fsS "$API_URL/health" >/dev/null
echo "API_HEALTH=ok"
