# Observabilidade

Esta etapa adiciona metricas simples de API e worker, alem de um roteiro de teste end-to-end.

## API

Endpoint:

```text
GET /metrics
```

Formato:

```text
Prometheus text format
```

Metricas atuais:

- `admanager_uptime_seconds`
- `admanager_http_requests_total`
- `admanager_http_request_seconds_total`
- `admanager_events_total`

## Worker

O worker grava metricas em:

```text
reports/worker-metrics.json
```

Campos atuais:

- `jobs_total`
- `jobs_error_total`

## Teste End-To-End De Laboratorio

Com API em execucao:

```bash
bash scripts/e2e-lab.sh
```

O roteiro valida:

- Health da API.
- Emissao de token.
- Identidade autenticada.
- Consulta de usuarios.
- Consulta de grupos.
- Consulta de computadores.
- Relatorio JSON.
- Endpoint de metricas.

## Cuidados

- O roteiro E2E atual executa apenas leituras e relatorio.
- Operacoes de escrita devem continuar em fluxo separado com `dry_run=true`.
- Para producao, proteja `/metrics` por rede interna ou proxy.
- Integre `/metrics` a Prometheus, Grafana ou stack equivalente.
