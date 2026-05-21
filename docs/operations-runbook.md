# Runbook Operacional

Este runbook define a ordem segura para subir, validar e liberar o Active Directory Manager para operadores.

## Objetivo

Garantir que API, frontend, worker, banco, fila, auditoria, inventario e operacoes em dry-run estejam prontos antes de uso real.

## Pre-Requisitos

- `.env` preenchido e fora do Git.
- Certificado CA do AD montado em `docker/secrets/ad_ca_cert`, quando `AD_TLS_REQUIRE_CERT=true`.
- Docker e Docker Compose acessiveis.
- Conta de servico AD com menor privilegio necessario.
- Ambiente de laboratorio definido para testes de escrita.
- Objetos de teste definidos para dry-run opcional.

## Ordem De Subida

1. Validar configuracao local:

```bash
python3 scripts/validate-env.py
```

2. Validar Compose:

```bash
docker compose config --quiet
```

3. Subir banco e Redis:

```bash
docker compose up -d database redis
```

4. Aplicar migracoes:

```bash
docker compose run --rm api python -m app.migrate
```

5. Subir API:

```bash
docker compose up -d api
```

6. Subir worker:

```bash
docker compose up -d worker
```

7. Subir frontend:

```bash
docker compose up -d frontend
```

8. Subir monitoramento, quando aplicavel:

```bash
docker compose --profile monitoring up -d prometheus alertmanager grafana
```

## Validacao Obrigatoria

Execute:

```bash
bash scripts/operational-readiness.sh
```

Resultado esperado:

```text
READINESS=ok
FAIL_COUNT=0
```

Avisos sao aceitaveis apenas quando o item foi conscientemente desabilitado ou nao faz parte do ambiente, por exemplo LDAP check em ambiente sem acesso ao AD.

## Validacao LDAP/LDAPS

Antes de liberar operacao real, execute:

```bash
RUN_LDAP_CHECK=true bash scripts/operational-readiness.sh
```

Resultado esperado:

```text
PASS=bind LDAP/LDAPS
```

Em producao, confirme:

- `AD_SERVER=ldaps://...:636`
- `AD_USE_LDAPS=true`
- `AD_TLS_REQUIRE_CERT=true`
- `REQUIRE_LDAPS_FOR_WRITES=true`

## Validacao De Leitura

Com a API no ar, o script integrado valida:

- `/health`
- `/auth/me`
- `/config/summary`
- `/users`
- `/groups`
- `/computers`
- `/reports/users`
- `/reports/inventory-snapshot`
- `/reports/worker-status`
- `/audit/events`
- `/metrics`

Se algum endpoint protegido retornar permissao negada, valide o perfil usado para emitir o token.

## Dry-Run Em Laboratorio

Use apenas objetos de laboratorio:

```bash
RUN_DRY_RUN_CHECKS=true \
LAB_USER=usuario.teste \
LAB_COMPUTER=PC-TESTE \
bash scripts/operational-readiness.sh
```

O dry-run deve:

- Validar o alvo no AD.
- Registrar auditoria.
- Retornar `dry_run=true`.
- Nao alterar o objeto.

## Criterios De Pronto Para Operador

O ambiente pode ser liberado para operadores quando:

- `scripts/operational-readiness.sh` termina com `READINESS=ok`.
- API, frontend, worker, banco e Redis estao com health check saudavel.
- `GET /ad/connection-test` retorna bind bem-sucedido.
- Auditoria persistente esta ativa.
- Worker gerou ou consegue ler status de jobs.
- Painel web mostra inventario ou informa claramente que o snapshot ainda nao foi gerado.
- Operacoes sensiveis funcionam em `dry_run=true`.
- Operadores foram orientados a nao usar escrita real sem aprovacao.
- Backup recente do PostgreSQL existe e restore foi testado em laboratorio.

## Backup E Restore

Antes de liberar operacao real, gere um backup:

```bash
bash scripts/backup-postgres.sh
```

Restore deve ser testado apenas em ambiente isolado:

```bash
CONFIRM_RESTORE=true bash scripts/restore-postgres.sh backups/postgres/arquivo.sql.gz
```

Detalhes em [backup-restore.md](backup-restore.md).

## Falhas Comuns

### Docker indisponivel

Verifique se o Docker Desktop ou daemon esta ativo e se o usuario tem permissao para acessar o socket.

### Snapshot de inventario ausente

Confirme se o worker esta ativo e se `WORKER_INVENTORY_SNAPSHOT_ENABLED=true`.

### Worker sem metricas

Confirme:

```env
WORKER_METRICS_ENABLED=true
WORKER_METRICS_PORT=9100
```

Depois valide:

```bash
curl http://localhost:9100/health
curl http://localhost:9100/metrics
```

### Permissao negada na interface

Revise o perfil usado para emitir o token:

- `viewer`: leitura e relatorios.
- `operator`: leitura, relatorios e operacoes sensiveis.
- `auditor`: leitura de auditoria e relatorios.
- `admin`: acesso completo.

### LDAPS falhando

Verifique:

- DNS do controlador de dominio.
- Porta 636.
- Cadeia da CA.
- `AD_CA_CERT_PATH`.
- Certificado com Server Authentication.

## Rotina De Operacao

Diariamente:

- Verificar painel web.
- Revisar jobs com falha.
- Conferir alertas Prometheus/Alertmanager.
- Conferir eventos recentes de auditoria.

Semanalmente:

- Revisar grupos sem responsavel.
- Revisar usuarios inativos.
- Revisar computadores sem metadados.
- Validar backup do banco.

Antes de mudancas sensiveis:

- Executar dry-run.
- Conferir auditoria.
- Validar aprovacao.
- Executar em janela aprovada.
- Conferir resultado e registrar evidencia.
