# Retencao E Dashboards

Esta etapa adiciona retencao automatica de auditoria e artefatos iniciais de Prometheus/Grafana.

## Retencao De Auditoria

Variaveis:

```env
AUDIT_RETENTION_DAYS=365
WORKER_AUDIT_RETENTION_ENABLED=true
WORKER_AUDIT_RETENTION_INTERVAL_SECONDS=86400
```

O worker executa o job:

```text
audit_retention
```

Ele remove registros antigos de:

```text
audit_events
```

com base em `AUDIT_RETENTION_DAYS`.

## Retencao Do Coletor De Logon

Variaveis:

```env
WORKSTATION_STATUS_RETENTION_DAYS=90
WORKER_WORKSTATION_STATUS_RETENTION_ENABLED=true
WORKER_WORKSTATION_STATUS_RETENTION_INTERVAL_SECONDS=86400
```

O worker executa o job:

```text
workstation_status_retention
```

Ele remove registros antigos de:

```text
workstation_status_events
```

com base em `WORKSTATION_STATUS_RETENTION_DAYS`.

## Prometheus

Arquivos:

```text
monitoring/prometheus/prometheus.yml
monitoring/prometheus/rules/admanager-alerts.yml
```

Alertas iniciais:

- HTTP 5xx.
- Falha de persistencia de auditoria.
- Ausencia de teste de conexao AD.
- Operacoes sensiveis.

## Grafana

Dashboard inicial:

```text
monitoring/grafana/dashboards/admanager-overview.json
```

Paineis:

- Uptime.
- Requisicoes HTTP.
- Eventos da aplicacao.

## Proximos Incrementos

- Exportar metricas do worker em formato Prometheus.
- Adicionar latencia LDAP por consulta.
- Criar painel de auditoria por operador.
- Criar alertas de jobs com falha.
