#!/usr/bin/env bash
set -euo pipefail

echo "== Python syntax =="
PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/private/tmp/admanager-pycache}" \
  python3 -m compileall api/app worker/app

PYTHON_VERSION_OK="$(python3 - <<'PY'
import sys
print("yes" if sys.version_info >= (3, 11) else "no")
PY
)"

if [ "${PYTHON_VERSION_OK}" = "yes" ] && python3 -m pytest --version >/dev/null 2>&1; then
  echo "== API tests =="
  PYTHONPATH=api python3 -m pytest api/tests

  echo "== Worker tests =="
  PYTHONPATH=worker python3 -m pytest worker/tests
else
  echo "WARN=pytest ignorado; requer Python >= 3.11 e pytest instalado"
fi

echo "== Compose =="
docker compose config --quiet

echo "== Operational readiness smoke =="
RUN_API_CHECKS=false \
RUN_LDAP_CHECK=false \
RUN_DRY_RUN_CHECKS=false \
RUN_FRONTEND_BUILD=false \
bash scripts/operational-readiness.sh

if command -v npm >/dev/null 2>&1; then
  echo "== Frontend build =="
  npm --prefix frontend install --cache "${NPM_CONFIG_CACHE:-/private/tmp/admanager-npm-cache}"
  npm --prefix frontend run build
else
  echo "WARN=npm nao encontrado; build frontend ignorado"
fi

echo "CI_LOCAL=ok"
