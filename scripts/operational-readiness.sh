#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8080}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
WORKER_URL="${WORKER_URL:-http://localhost:9100}"
RUN_DOCKER="${RUN_DOCKER:-true}"
RUN_FRONTEND_BUILD="${RUN_FRONTEND_BUILD:-true}"
RUN_LDAP_CHECK="${RUN_LDAP_CHECK:-false}"
RUN_API_CHECKS="${RUN_API_CHECKS:-true}"
RUN_DRY_RUN_CHECKS="${RUN_DRY_RUN_CHECKS:-false}"
RUN_BACKUP_CHECK="${RUN_BACKUP_CHECK:-true}"
LAB_USER="${LAB_USER:-}"
LAB_COMPUTER="${LAB_COMPUTER:-}"

pass_count=0
warn_count=0
fail_count=0

section() {
  printf "\n== %s ==\n" "$1"
}

pass() {
  pass_count=$((pass_count + 1))
  printf "PASS=%s\n" "$1"
}

warn() {
  warn_count=$((warn_count + 1))
  printf "WARN=%s\n" "$1"
}

fail() {
  fail_count=$((fail_count + 1))
  printf "FAIL=%s\n" "$1"
}

read_env_value() {
  local key="$1"
  python3 - "$key" <<'PY'
from pathlib import Path
import sys

key = sys.argv[1]
path = Path(".env")
if not path.exists():
    raise SystemExit(0)

for raw in path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    name, value = line.split("=", 1)
    if name.strip() == key:
        print(value.strip().strip('"').strip("'"))
        break
PY
}

curl_json() {
  local url="$1"
  local token="${2:-}"
  if [[ -n "$token" ]]; then
    curl -fsS "$url" -H "Authorization: Bearer $token" >/dev/null
  else
    curl -fsS "$url" >/dev/null
  fi
}

section "Ambiente"
if [[ -f .env ]]; then
  pass ".env encontrado"
else
  fail ".env nao encontrado"
fi

if python3 scripts/validate-env.py >/tmp/admanager-validate-env.out 2>&1; then
  pass "variaveis de ambiente validas"
else
  fail "variaveis de ambiente invalidas"
  sed -n '1,40p' /tmp/admanager-validate-env.out
fi

section "Sintaxe"
if PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/private/tmp/admanager-pycache}" \
  python3 -m compileall -q api/app worker/app; then
  pass "codigo Python compila"
else
  fail "falha de sintaxe Python"
fi

if [[ "$RUN_FRONTEND_BUILD" == "true" ]]; then
  if command -v npm >/dev/null 2>&1; then
    if npm --prefix frontend run build >/tmp/admanager-frontend-build.out 2>&1; then
      pass "build do frontend"
    else
      fail "build do frontend"
      sed -n '1,80p' /tmp/admanager-frontend-build.out
    fi
  else
    warn "npm nao encontrado; build frontend ignorado"
  fi
else
  warn "build frontend ignorado por RUN_FRONTEND_BUILD=false"
fi

section "Docker"
if [[ "$RUN_DOCKER" == "true" ]]; then
  if command -v docker >/dev/null 2>&1; then
    if docker compose config --quiet >/tmp/admanager-compose-config.out 2>&1; then
      pass "compose.yaml valido"
    else
      fail "compose.yaml invalido"
      sed -n '1,80p' /tmp/admanager-compose-config.out
    fi

    if docker compose ps >/tmp/admanager-compose-ps.out 2>&1; then
      pass "docker compose acessivel"
      sed -n '1,20p' /tmp/admanager-compose-ps.out
    else
      warn "docker compose indisponivel ou sem permissao"
    fi
  else
    warn "docker nao encontrado"
  fi
else
  warn "checks Docker ignorados por RUN_DOCKER=false"
fi

section "LDAP"
if [[ "$RUN_LDAP_CHECK" == "true" ]]; then
  if bash scripts/check-ldap.sh >/tmp/admanager-ldap.out 2>&1; then
    pass "bind LDAP/LDAPS"
  else
    fail "bind LDAP/LDAPS"
    sed -n '1,80p' /tmp/admanager-ldap.out
  fi
else
  warn "bind LDAP/LDAPS ignorado por RUN_LDAP_CHECK=false"
fi

section "API"
token=""
if [[ "$RUN_API_CHECKS" == "true" ]]; then
  if curl_json "$API_URL/health"; then
    pass "API health"
  else
    fail "API health em $API_URL"
  fi

  bootstrap_token="$(read_env_value APP_BOOTSTRAP_ADMIN_TOKEN)"
  if [[ -n "$bootstrap_token" ]]; then
    if token="$(curl -fsS -X POST "$API_URL/auth/token" \
      -H "Content-Type: application/json" \
      -H "X-Bootstrap-Token: $bootstrap_token" \
      -d '{"subject":"readiness.local","roles":["admin"]}' \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')" >/tmp/admanager-token.out 2>&1; then
      pass "emissao de token admin"
    else
      fail "emissao de token admin"
      token=""
    fi
  else
    warn "APP_BOOTSTRAP_ADMIN_TOKEN ausente; endpoints protegidos ignorados"
  fi

  if [[ -n "$token" ]]; then
    for item in \
      "/auth/me" \
      "/config/summary" \
      "/users?status=active&limit=1" \
      "/groups?status=all&limit=1" \
      "/computers?status=all&limit=1" \
      "/reports/users?status=active&format=json&limit=1" \
      "/reports/inventory-snapshot" \
      "/reports/worker-status?limit=5" \
      "/audit/events?limit=5"; do
      if curl_json "$API_URL$item" "$token"; then
        pass "GET $item"
      else
        warn "GET $item indisponivel"
      fi
    done

    if curl_json "$API_URL/metrics"; then
      pass "metricas da API"
    else
      warn "metricas da API indisponiveis"
    fi
  fi
else
  warn "checks API ignorados por RUN_API_CHECKS=false"
fi

section "Worker E Frontend"
if curl_json "$WORKER_URL/health"; then
  pass "worker health"
else
  warn "worker health indisponivel em $WORKER_URL"
fi

if curl_json "$WORKER_URL/metrics"; then
  pass "worker metrics"
else
  warn "worker metrics indisponivel em $WORKER_URL"
fi

if curl -fsS -I "$FRONTEND_URL" >/dev/null 2>&1; then
  pass "frontend responde"
else
  warn "frontend indisponivel em $FRONTEND_URL"
fi

section "Dry-run Opcional"
if [[ "$RUN_DRY_RUN_CHECKS" == "true" ]]; then
  if [[ -z "$token" ]]; then
    fail "dry-run requer token admin emitido"
  else
    if [[ -n "$LAB_USER" ]]; then
      if curl -fsS -X POST "$API_URL/users/$LAB_USER/unlock" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d '{"confirm":true,"dry_run":true,"reason":"Readiness dry-run de laboratorio"}' >/dev/null; then
        pass "dry-run usuario"
      else
        fail "dry-run usuario"
      fi
    else
      warn "LAB_USER ausente; dry-run de usuario ignorado"
    fi

    if [[ -n "$LAB_COMPUTER" ]]; then
      if curl -fsS -X POST "$API_URL/computers/$LAB_COMPUTER/enable" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d '{"confirm":true,"dry_run":true,"reason":"Readiness dry-run de laboratorio"}' >/dev/null; then
        pass "dry-run computador"
      else
        fail "dry-run computador"
      fi
    else
      warn "LAB_COMPUTER ausente; dry-run de computador ignorado"
    fi
  fi
else
  warn "dry-run de laboratorio ignorado por RUN_DRY_RUN_CHECKS=false"
fi

section "Backup"
if [[ "$RUN_BACKUP_CHECK" == "true" ]]; then
  latest_backup="$(find backups/postgres -type f -name '*.sql.gz' -print 2>/dev/null | sort | tail -1 || true)"
  if [[ -n "$latest_backup" ]]; then
    pass "backup PostgreSQL encontrado: $latest_backup"
    if [[ -f "$latest_backup.sha256" ]]; then
      pass "checksum do backup encontrado"
    else
      warn "checksum do backup ausente"
    fi
  else
    warn "nenhum backup PostgreSQL encontrado em backups/postgres"
  fi
else
  warn "check de backup ignorado por RUN_BACKUP_CHECK=false"
fi

section "Resumo"
echo "PASS_COUNT=$pass_count"
echo "WARN_COUNT=$warn_count"
echo "FAIL_COUNT=$fail_count"

if [[ "$fail_count" -gt 0 ]]; then
  echo "READINESS=failed"
  exit 1
fi

echo "READINESS=ok"
