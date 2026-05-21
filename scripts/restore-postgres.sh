#!/usr/bin/env bash
set -euo pipefail

COMPOSE_SERVICE="${POSTGRES_COMPOSE_SERVICE:-database}"
BACKUP_FILE="${1:-}"
CONFIRM_RESTORE="${CONFIRM_RESTORE:-false}"

if [[ -z "$BACKUP_FILE" ]]; then
  echo "STATUS=error"
  echo "ERROR=uso: CONFIRM_RESTORE=true scripts/restore-postgres.sh backups/postgres/arquivo.sql.gz"
  exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "STATUS=error"
  echo "ERROR=arquivo de backup nao encontrado"
  exit 1
fi

if [[ "$CONFIRM_RESTORE" != "true" ]]; then
  echo "STATUS=blocked"
  echo "ERROR=restore exige CONFIRM_RESTORE=true"
  exit 1
fi

POSTGRES_DB="$(docker compose exec -T "$COMPOSE_SERVICE" printenv POSTGRES_DB)"
POSTGRES_USER="$(docker compose exec -T "$COMPOSE_SERVICE" printenv POSTGRES_USER)"

if [[ -z "$POSTGRES_DB" || -z "$POSTGRES_USER" ]]; then
  echo "STATUS=error"
  echo "ERROR=POSTGRES_DB ou POSTGRES_USER indisponivel no container"
  exit 1
fi

if [[ -f "$BACKUP_FILE.sha256" ]]; then
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c "$BACKUP_FILE.sha256"
  else
    shasum -a 256 -c "$BACKUP_FILE.sha256"
  fi
fi

echo "STATUS=running"
echo "TARGET_DB=$POSTGRES_DB"
echo "BACKUP_FILE=$BACKUP_FILE"

case "$BACKUP_FILE" in
  *.gz)
    gzip -dc "$BACKUP_FILE" | docker compose exec -T "$COMPOSE_SERVICE" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1
    ;;
  *)
    docker compose exec -T "$COMPOSE_SERVICE" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 < "$BACKUP_FILE"
    ;;
esac

echo "STATUS=ok"
