# Auditoria Persistente

Esta etapa grava eventos de auditoria no PostgreSQL e permite consulta protegida pela API.

## Configuracao

Variaveis relevantes:

```env
DATABASE_URL=postgresql://admanager:change-me@database:5432/admanager
AUDIT_DATABASE_ENABLED=true
```

Quando `AUDIT_DATABASE_ENABLED=true`, a API tenta criar automaticamente a tabela:

```text
audit_events
```

Se o banco estiver indisponivel, a API continua registrando eventos em stdout e emite um evento `audit_persist_failed`.

## Eventos Gravados

Eventos atuais incluem:

- Requisicoes HTTP.
- Emissao de token.
- Teste de conexao AD.
- Consultas de usuarios, grupos e computadores.
- Geracao de relatorios.
- Operacoes controladas em usuarios, grupos e computadores.

## Consultar Auditoria

Permissao necessaria:

```text
read:audit
```

Exemplo:

```bash
curl "http://localhost:8080/audit/events?limit=100" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Filtros disponiveis:

- `event`
- `operator`
- `target`
- `correlation_id`
- `start`
- `end`
- `limit`

Exemplo por operador:

```bash
curl "http://localhost:8080/audit/events?operator=admin.local&limit=50" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Exemplo por periodo:

```bash
curl "http://localhost:8080/audit/events?start=2026-05-19T00:00:00-03:00&end=2026-05-19T23:59:59-03:00" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Tabela

Campos principais:

- `id`
- `occurred_at`
- `event`
- `operator`
- `target`
- `correlation_id`
- `payload`

## Cuidados

- Senhas, tokens e segredos sao mascarados antes da persistencia.
- A auditoria em banco nao substitui logs de infraestrutura.
- Configure backup do PostgreSQL antes de uso real.
- Use filtros ao consultar historico grande.
