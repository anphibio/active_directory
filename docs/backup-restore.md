# Backup, Restore E Retencao

Este guia cobre backup e restore operacional do PostgreSQL usado para auditoria, historico e metadados.

## Escopo

O backup cobre o banco PostgreSQL do servico `database`.

Nao cobre automaticamente:

- `.env`.
- Docker secrets.
- Certificados.
- Arquivos gerados em `reports`.
- Volumes de Prometheus, Grafana ou Alertmanager.

Esses itens devem ter politica propria de backup.

## Backup

Com o banco em execucao:

```bash
bash scripts/backup-postgres.sh
```

Antes da primeira liberacao para operadores, esse comando deve ser executado ao menos uma vez.

Saida esperada:

```text
STATUS=ok
BACKUP_FILE=backups/postgres/admanager-YYYYMMDDHHMMSS.sql.gz
CHECKSUM_FILE=backups/postgres/admanager-YYYYMMDDHHMMSS.sql.gz.sha256
```

O script:

- Usa `pg_dump` dentro do container `database`.
- Nao imprime senha.
- Gera arquivo comprimido.
- Gera checksum SHA-256.
- Salva em `backups/postgres` por padrao.

Para usar outro diretorio:

```bash
BACKUP_DIR=/caminho/seguro/admanager bash scripts/backup-postgres.sh
```

## Restore

Restore exige confirmacao explicita:

```bash
CONFIRM_RESTORE=true bash scripts/restore-postgres.sh backups/postgres/admanager-YYYYMMDDHHMMSS.sql.gz
```

O script:

- Valida checksum quando o arquivo `.sha256` existir.
- Usa `psql` dentro do container `database`.
- Para no primeiro erro SQL com `ON_ERROR_STOP=1`.

## Validacao De Restore Em Laboratorio

1. Suba um ambiente isolado.
2. Restaure o backup.
3. Aplique migracoes, se necessario:

```bash
docker compose run --rm api python -m app.migrate
```

4. Valide a API:

```bash
bash scripts/operational-readiness.sh
```

5. Consulte auditoria:

```bash
curl "http://localhost:8080/audit/events?limit=5" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Retencao Recomendada

Defina retencao conforme politica corporativa. Sugestao inicial:

- Backups diarios: 30 dias.
- Backups semanais: 12 semanas.
- Backups mensais: 12 meses.
- Relatorios CSV: `REPORT_RETENTION_DAYS`.
- Auditoria em banco: `AUDIT_RETENTION_DAYS`.
- Snapshots de inventario: reter conforme capacidade e necessidade de historico.

## Cuidados

- Nunca commitar backups.
- Armazenar backups fora do host quando houver operacao real.
- Criptografar backups em repouso.
- Testar restore periodicamente.
- Proteger checksums junto com os backups.
- Validar permissao de acesso ao diretório de backup.
