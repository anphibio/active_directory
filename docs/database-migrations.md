# Migracoes Formais De Banco

Esta etapa versiona o schema do banco de dados.

## Estrutura

Migrações ficam em:

```text
api/migrations/
```

O controle de versão é feito pela tabela:

```text
schema_migrations
```

## Migrações Atuais

```text
001_audit_events.sql
```

Ela cria:

- `schema_migrations`
- `audit_events`
- Indices de consulta da auditoria

## Aplicar Migrações

Dentro do container da API:

```bash
docker compose run --rm api python -m app.migrate
```

No startup da API, o mesmo runner também é executado automaticamente.

## Saida Esperada

```json
{
  "status": "ok",
  "available": ["001_audit_events"],
  "applied": ["001_audit_events"]
}
```

Quando a migração já foi aplicada, `applied` retorna vazio.

## Criar Nova Migração

Use arquivos numerados:

```text
002_nome_da_migracao.sql
003_nome_da_migracao.sql
```

Regras:

- Migrações devem ser idempotentes sempre que possível.
- Não altere migrações já aplicadas em ambiente compartilhado.
- Crie uma nova migração para mudanças posteriores.
- Evite dados sensíveis em SQL.
