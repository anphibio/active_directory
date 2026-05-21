#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8080}"

if [[ ! -f .env ]]; then
  echo "STATUS=error"
  echo "ERROR=.env nao encontrado"
  exit 1
fi

BOOTSTRAP_TOKEN="$(python3 - <<'PY'
from pathlib import Path
values = {}
for raw in Path('.env').read_text(encoding='utf-8').splitlines():
    line = raw.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    key, value = line.split('=', 1)
    values[key.strip()] = value.strip().strip('"').strip("'")
print(values.get('APP_BOOTSTRAP_ADMIN_TOKEN', ''))
PY
)"

if [[ -z "$BOOTSTRAP_TOKEN" ]]; then
  echo "STATUS=error"
  echo "ERROR=APP_BOOTSTRAP_ADMIN_TOKEN ausente"
  exit 1
fi

TOKEN="$(curl -fsS -X POST "$API_URL/auth/token" \
  -H "Content-Type: application/json" \
  -H "X-Bootstrap-Token: $BOOTSTRAP_TOKEN" \
  -d '{"subject":"e2e.lab","roles":["admin"]}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"

curl -fsS "$API_URL/health" >/dev/null
echo "HEALTH=ok"

curl -fsS "$API_URL/auth/me" -H "Authorization: Bearer $TOKEN" >/dev/null
echo "AUTH=ok"

curl -fsS "$API_URL/users?status=active&limit=1" -H "Authorization: Bearer $TOKEN" >/dev/null
echo "USERS_READ=ok"

curl -fsS "$API_URL/groups?status=all&limit=1" -H "Authorization: Bearer $TOKEN" >/dev/null
echo "GROUPS_READ=ok"

curl -fsS "$API_URL/computers?status=all&limit=1" -H "Authorization: Bearer $TOKEN" >/dev/null
echo "COMPUTERS_READ=ok"

curl -fsS "$API_URL/reports/users?status=active&format=json&limit=1" -H "Authorization: Bearer $TOKEN" >/dev/null
echo "REPORTS=ok"

curl -fsS "$API_URL/metrics" >/dev/null
echo "METRICS=ok"

echo "E2E_LAB=ok"
