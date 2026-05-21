# Jobs Agendados No Worker

Esta etapa adiciona um scheduler simples dentro do container `worker`.

## Configuracao

Variaveis principais:

```env
WORKER_HEARTBEAT_SECONDS=60
WORKER_API_BASE_URL=http://api:8080
WORKER_API_SUBJECT=admanager-worker
WORKER_API_TIMEOUT_SECONDS=30
WORKER_API_TOKEN_MODE=local
WORKER_API_TOKEN_EXPIRE_SECONDS=3600
WORKER_SCHEDULER_INTERVAL_SECONDS=30
WORKER_REPORT_CLEANUP_ENABLED=true
WORKER_INVENTORY_SNAPSHOT_ENABLED=true
WORKER_INVENTORY_SNAPSHOT_INTERVAL_SECONDS=86400
WORKER_WORKSTATION_STATUS_RETENTION_ENABLED=true
WORKER_WORKSTATION_STATUS_RETENTION_INTERVAL_SECONDS=86400
WORKER_INVENTORY_QUERY_LIMIT=500
WORKER_INVENTORY_INACTIVE_DAYS=90
WORKER_INVENTORY_MACHINE_PASSWORD_DAYS=90
REPORT_RETENTION_DAYS=90
WORKSTATION_STATUS_RETENTION_DAYS=90
REPORT_OUTPUT_DIR=/app/reports
```

## Jobs

### `report_cleanup`

Remove arquivos `.csv` antigos do diretorio de relatorios com base em:

```env
REPORT_RETENTION_DAYS=90
```

### `inventory_snapshot`

Cria um arquivo JSON de snapshot operacional no diretorio de relatorios, usando a API interna para consultar o Active Directory.

Arquivos gerados:

```text
reports/inventory-snapshot-YYYYMMDDHHMMSS.json
reports/inventory-snapshot-latest.json
```

Resumo coletado:

- Usuarios por status: todos, ativos, desabilitados, bloqueados, inativos, nunca logaram e senha nunca expira.
- Grupos por status: todos, vazios, com membros, sem descricao e sem responsavel.
- Computadores por status: todos, ativos, desabilitados, inativos, nunca logaram, servidores, workstations, controladores de dominio, senha de maquina antiga e metadados ausentes.

Observacao: cada consulta respeita `WORKER_INVENTORY_QUERY_LIMIT`. Se o limite for atingido, o snapshot marca a consulta como `capped=true`.

### `workstation_status_retention`

Remove eventos antigos do coletor de logon das estacoes com base em:

```env
WORKSTATION_STATUS_RETENTION_DAYS=90
```

Esse job limpa registros da tabela:

```text
workstation_status_events
```

Ele nao altera objetos no Active Directory.

## Historico De Jobs

O worker grava execucoes em:

```text
reports/worker-jobs.jsonl
```

## API

O status consolidado do worker pode ser consultado pela API:

```bash
curl "http://localhost:8080/reports/worker-status?limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

O retorno inclui:

- Total de execucoes.
- Total de falhas.
- Ultimos jobs.
- Ultimo sucesso por job.
- Ultima falha por job.

Esse endpoint e usado pelo painel operacional do frontend.

Metricas expostas em `/metrics`:

- `admanager_inventory_snapshot_timestamp`
- `admanager_inventory_objects`
- `admanager_inventory_query_capped`

Cada linha contem:

- Timestamp.
- Nome do job.
- Status.
- Campos adicionais da execucao.

## Execucao

```bash
docker compose up -d worker
```

Logs:

```bash
docker compose logs -f worker
```

## Cuidados

- Os jobs atuais nao alteram Active Directory.
- A limpeza remove apenas arquivos `.csv` no diretorio de relatorios.
- A retencao de status das estacoes remove apenas historico antigo do coletor.
- A frequencia deve ser ajustada por ambiente.
- Jobs mais pesados devem futuramente usar fila e controle de concorrencia.
