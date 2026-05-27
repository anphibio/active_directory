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

## IP De Origem Atras De Proxy

A coluna `Origem` usa o IP calculado pela API no momento da requisicao.

Quando a aplicacao estiver atras de Nginx ou outro proxy reverso, configure o proxy para enviar:

```nginx
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

E configure a API para confiar somente na rede/IP do proxy:

```env
TRUSTED_PROXY_CIDRS=172.19.0.0/16
```

Com isso, a API usa o primeiro IP valido de `X-Forwarded-For` como origem real do operador. Se a
requisicao chegar diretamente de um cliente fora de `TRUSTED_PROXY_CIDRS`, os headers sao ignorados
e a origem registrada sera o IP direto da conexao.

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
