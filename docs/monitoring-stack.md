# Stack De Monitoramento

Esta etapa integra Prometheus, Grafana, metricas do worker e Alertmanager ao Docker Compose.

## Subir Com Perfil

```bash
docker compose --profile monitoring up -d prometheus alertmanager grafana
```

## Subir Com Arquivo Dedicado

```bash
docker compose -f compose.yaml -f compose.monitoring.yaml up -d prometheus alertmanager grafana
```

## Acessos

Prometheus:

```text
http://localhost:9090
```

Grafana:

```text
http://localhost:3001
```

Alertmanager:

```text
http://localhost:9093
```

Usuario e senha:

```env
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=change-me
```

Troque a senha antes de uso real.

## Provisionamento

Datasource:

```text
monitoring/grafana/provisioning/datasources/prometheus.yml
```

Dashboard:

```text
monitoring/grafana/provisioning/dashboards/admanager.yml
monitoring/grafana/dashboards/admanager-overview.json
```

Prometheus:

```text
monitoring/prometheus/prometheus.yml
monitoring/prometheus/rules/admanager-alerts.yml
```

Alertmanager:

```text
monitoring/alertmanager/Dockerfile
monitoring/alertmanager/entrypoint.sh
monitoring/alertmanager/templates/admanager.tmpl
```

## Metricas Coletadas

A API expoe metricas em:

```text
http://localhost:8080/metrics
```

O worker expoe metricas em:

```text
http://localhost:9100/metrics
```

No Docker, o worker escuta internamente em `WORKER_METRICS_LISTEN_PORT=9100`. A variavel `WORKER_METRICS_PORT` controla a porta publicada no host.

Principais metricas do worker:

- `admanager_worker_uptime_seconds`
- `admanager_worker_jobs_total`
- `admanager_worker_job_last_run_timestamp`
- `admanager_inventory_snapshot_timestamp`
- `admanager_inventory_objects`
- `admanager_inventory_query_capped`
- `admanager_inventory_query_errors`
- `admanager_inventory_segment_objects`
- `admanager_inventory_segment_query_errors`
- `admanager_inventory_delta_objects`

## Alertas Iniciais

- API indisponivel.
- Worker indisponivel.
- Erros HTTP 5xx.
- Falha de persistencia de auditoria.
- Falhas em jobs do worker.
- Snapshot de inventario AD desatualizado.
- Consulta de inventario AD limitada pelo `WORKER_INVENTORY_QUERY_LIMIT`.
- Falha em consulta de inventario AD.
- Falha em consulta de inventario segmentado por OU.
- Variacao anormal de inventario entre snapshots.
- Ausencia recente de teste de conexao com AD.
- Operacoes sensiveis executadas ou simuladas.

## Validacao

```bash
curl http://localhost:9090/-/ready
curl http://localhost:3001/api/health
curl http://localhost:9093/-/ready
curl http://localhost:9100/metrics
```

## Observacoes

- `/metrics` deve ficar restrito por rede em producao.
- Grafana deve usar senha forte.
- Configure retencao do Prometheus conforme volume disponivel.
- O Alertmanager gera a configuracao final a partir das variaveis do `.env`.
- Integre e-mail, webhook, Teams bridge ou Slack bridge conforme o canal corporativo.
- Mais detalhes em [alert-integrations.md](alert-integrations.md).
