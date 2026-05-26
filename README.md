# Active Directory Manager

Sistema conteinerizado para gerenciamento, auditoria e relatorios de usuarios, grupos e computadores do Active Directory.

## Objetivo

O projeto sera uma plataforma profissional para operacoes de infraestrutura em Active Directory, com foco em seguranca, auditoria, relatorios e execucao 100% em Docker.

## Estado Atual

O projeto ja possui API protegida, worker, frontend operacional, auditoria persistente, relatorios, inventario AD, coletor de logon das estacoes, monitoramento, backup/restore e scripts de validacao integrada.

Consulte o plano em [docs/development-plan.md](docs/development-plan.md).

## Estrutura

```text
.
├── api/                 # Backend e regras de negocio
├── worker/              # Jobs, relatorios e tarefas assincronas
├── frontend/            # Interface web
├── docs/                # Documentacao operacional
├── scripts/             # Scripts de apoio
├── docker/secrets/      # Certificados e secrets locais ignorados pelo Git
├── reports/             # Saida local de relatorios ignorada pelo Git
├── compose.yaml
├── .env.example
└── AGENTS.md
```

## Configuracao Inicial

Crie seu arquivo local de ambiente a partir do exemplo:

```bash
cp .env.example .env
```

Depois ajuste os valores de acordo com o ambiente. Nunca commite `.env`.

## Execucao

Suba o ambiente:

```bash
docker compose up -d
```

Verifique os servicos:

```bash
docker compose ps
```

A API ficara disponivel em:

```text
http://localhost:8080
```

O frontend ficara disponivel em:

```text
http://localhost:3000
```

## Validacao De Ambiente

Para verificar se as variaveis obrigatorias de Active Directory estao preenchidas:

```bash
docker compose run --rm api python -m app.validate_environment
```

Para testar conectividade e bind com o Active Directory, com a API em execucao:

```bash
curl http://localhost:8080/ad/connection-test
```

Mais detalhes em [docs/ad-connectivity.md](docs/ad-connectivity.md).

## Seguranca

A API usa token assinado e perfis de acesso desde a etapa 3.

Para emitir um token inicial, use `APP_BOOTSTRAP_ADMIN_TOKEN` do `.env`:

```bash
curl -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/json" \
  -H "X-Bootstrap-Token: $APP_BOOTSTRAP_ADMIN_TOKEN" \
  -d '{"subject":"admin.local","roles":["admin"]}'
```

Mais detalhes em [docs/security-model.md](docs/security-model.md).

## Consultas De Usuarios

Com um token valido, liste usuarios do Active Directory:

```bash
curl "http://localhost:8080/users?status=active&limit=100" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Mais detalhes em [docs/users.md](docs/users.md).

## Consultas De Grupos

Com um token valido, liste grupos do Active Directory:

```bash
curl "http://localhost:8080/groups?status=all&limit=100" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Mais detalhes em [docs/groups.md](docs/groups.md).

## Consultas De Computadores

Com um token valido, liste computadores do Active Directory:

```bash
curl "http://localhost:8080/computers?status=active&limit=100" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Mais detalhes em [docs/computers.md](docs/computers.md).

## Relatorios

Gere relatorios em JSON ou CSV:

```bash
curl "http://localhost:8080/reports/users?status=active&format=csv" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -o usuarios-ativos.csv
```

Mais detalhes em [docs/reports.md](docs/reports.md).

## Operacoes Sensíveis Em Usuarios

As operacoes de escrita exigem permissao, confirmacao e justificativa. Por padrao, use `dry_run=true`:

```bash
curl -X POST "http://localhost:8080/users/usuario.teste/unlock" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true,"dry_run":true,"reason":"Validacao operacional em modo simulado"}'
```

Mais detalhes em [docs/user-operations.md](docs/user-operations.md).

## Operacoes Controladas Em Grupos

Adicione ou remova usuarios de grupos com confirmacao, justificativa e dry-run:

```bash
curl -X POST "http://localhost:8080/groups/NOME_DO_GRUPO/members/add" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sam_account_name":"usuario.teste","confirm":true,"dry_run":true,"reason":"Validacao operacional em modo simulado"}'
```

Mais detalhes em [docs/group-operations.md](docs/group-operations.md).

## Operacoes Controladas Em Computadores

Habilite, desabilite ou atualize metadados de computadores com dry-run e auditoria:

```bash
curl -X POST "http://localhost:8080/computers/NOME-DO-PC/metadata" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true,"dry_run":true,"reason":"Validacao operacional em modo simulado","description":"Estacao revisada"}'
```

Mais detalhes em [docs/computer-operations.md](docs/computer-operations.md).

## Interface Web

A interface web consome a API protegida:

```text
http://localhost:3000
```

Mais detalhes em [docs/frontend.md](docs/frontend.md).

## Auditoria Persistente

A API grava eventos de auditoria no PostgreSQL e permite consulta protegida:

```bash
curl "http://localhost:8080/audit/events?limit=100" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Mais detalhes em [docs/audit.md](docs/audit.md).

## Worker E Jobs

O worker executa jobs agendados, como limpeza de relatórios antigos:

```bash
docker compose up -d worker
```

Mais detalhes em [docs/worker-jobs.md](docs/worker-jobs.md).

## Inventário AD Agendado

O worker coleta um resumo periódico de usuarios, grupos e computadores do AD via API interna.

Mais detalhes em [docs/ad-inventory-worker.md](docs/ad-inventory-worker.md).

## Coletor De Logon Das Estacoes

Estacoes podem enviar usuario, computador, IP e horario via GPO para enriquecer a tela de usuarios com o computador de logon mais recente.

Mais detalhes em [docs/workstation-logon-collector.md](docs/workstation-logon-collector.md).

## Migrações De Banco

Aplicar migrações manualmente:

```bash
docker compose run --rm api python -m app.migrate
```

Mais detalhes em [docs/database-migrations.md](docs/database-migrations.md).

## Backup E Restore

Gerar backup do PostgreSQL:

```bash
bash scripts/backup-postgres.sh
```

Mais detalhes em [docs/backup-restore.md](docs/backup-restore.md).

## Testes De Integração E Produção

Valide o ambiente local:

```bash
python3 scripts/validate-env.py
bash scripts/check-ldap.sh
bash scripts/check-api.sh
```

Validacao integrada de prontidao operacional:

```bash
bash scripts/operational-readiness.sh
```

Mais detalhes em [docs/integration-tests.md](docs/integration-tests.md), [docs/production-checklist.md](docs/production-checklist.md) e [docs/operations-runbook.md](docs/operations-runbook.md).

## CI E Deploy

Execute uma validação local equivalente à pipeline:

```bash
bash scripts/ci-local.sh
```

Deploy inicial com build local no servidor:

```bash
cp .env.example .env
# edite .env com APP_ENV=production, LDAPS, segredos e URLs reais
docker compose up -d --build database redis
docker compose run --rm api python -m app.migrate
docker compose up -d --build api worker frontend
```

Deploy com imagens versionadas:

```bash
IMAGE_REGISTRY=ghcr.io \
IMAGE_NAMESPACE=anphibio/active_directory \
IMAGE_TAG=v0.1.0 \
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

Mais detalhes em [docs/deploy.md](docs/deploy.md).

## Testes Automatizados

A suíte cobre filtros LDAP, conversão de atributos AD, autenticação, permissões, operações sensíveis em dry-run e métricas do worker.

```bash
PYTHONPATH=api pytest api/tests
PYTHONPATH=worker pytest worker/tests
```

## Observabilidade E E2E

Metricas da API:

```bash
curl http://localhost:8080/metrics
```

Teste end-to-end de laboratorio:

```bash
bash scripts/e2e-lab.sh
```

Mais detalhes em [docs/observability.md](docs/observability.md).

## Hardening De Produção

Valide se o ambiente está pronto para produção:

```bash
docker compose run --rm api python -m app.validate_environment
```

Mais detalhes em [docs/hardening.md](docs/hardening.md).

## Retenção E Dashboards

Artefatos iniciais de Prometheus/Grafana e retenção automática de auditoria:

```text
monitoring/prometheus/prometheus.yml
monitoring/grafana/dashboards/admanager-overview.json
```

Mais detalhes em [docs/retention-dashboards.md](docs/retention-dashboards.md).

## Stack De Monitoramento

Suba Prometheus, Alertmanager e Grafana:

```bash
docker compose --profile monitoring up -d prometheus alertmanager grafana
```

Mais detalhes em [docs/monitoring-stack.md](docs/monitoring-stack.md).

## Integrações De Alertas

O Alertmanager pode enviar alertas por webhook generico ou SMTP usando variaveis do `.env`.

Mais detalhes em [docs/alert-integrations.md](docs/alert-integrations.md).

## Proximas Etapas

1. Validar o coletor de logon em laboratorio com um grupo piloto de estacoes.
2. Definir retencao operacional para `workstation_status_events`.
