#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-backups/postgres}"
COMPOSE_SERVICE="${POSTGRES_COMPOSE_SERVICE:-database}"
TIMESTAMP="$(date -u +%Y%m%d%H%M%S)"

mkdir -p "$BACKUP_DIR"

POSTGRES_DB="$(docker compose exec -T "$COMPOSE_SERVICE" printenv POSTGRES_DB)"
POSTGRES_USER="$(docker compose exec -T "$COMPOSE_SERVICE" printenv POSTGRES_USER)"

if [[ -z "$POSTGRES_DB" || -z "$POSTGRES_USER" ]]; then
  echo "STATUS=error"
  echo "ERROR=POSTGRES_DB ou POSTGRES_USER indisponivel no container"
  exit 1
fi

OUTPUT_FILE="$BACKUP_DIR/${POSTGRES_DB}-${TIMESTAMP}.sql.gz"

echo "STATUS=running"
echo "BACKUP_FILE=$OUTPUT_FILE"

docker compose exec -T "$COMPOSE_SERVICE" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges \
  | gzip -9 > "$OUTPUT_FILE"

if [[ ! -s "$OUTPUT_FILE" ]]; then
  echo "STATUS=error"
  echo "ERROR=backup vazio"
  exit 1
fi

sha256sum "$OUTPUT_FILE" > "$OUTPUT_FILE.sha256" 2>/dev/null || shasum -a 256 "$OUTPUT_FILE" > "$OUTPUT_FILE.sha256"

echo "STATUS=ok"
echo "BACKUP_FILE=$OUTPUT_FILE"
echo "CHECKSUM_FILE=$OUTPUT_FILE.sha256"
