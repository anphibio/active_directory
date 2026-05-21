# Operacoes Controladas Em Grupos

Esta etapa adiciona operacoes controladas para associar e remover usuarios de grupos do Active Directory.

## Permissao Necessaria

Todos os endpoints exigem:

```text
write:groups
```

Perfis com acesso nesta fase:

- `operator`
- `admin`

## Protecoes

Todas as operacoes exigem:

- Token valido.
- Permissao `write:groups`.
- `confirm=true`.
- `reason` com justificativa.
- Auditoria estruturada.
- `dry_run=true` por padrao.

Grupos sensiveis exigem tambem:

```json
{
  "protected_group_confirm": true
}
```

Os padroes de grupos protegidos sao configurados por:

```env
PROTECTED_GROUP_PATTERNS=Domain Admins,Enterprise Admins,Schema Admins,Administrators,Account Operators,Server Operators,Backup Operators
```

## Adicionar Usuario Ao Grupo

```bash
curl -X POST "http://localhost:8080/groups/NOME_DO_GRUPO/members/add" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sam_account_name": "usuario.teste",
    "confirm": true,
    "dry_run": true,
    "reason": "Chamado INC123456 aprovado pelo gestor"
  }'
```

## Remover Usuario Do Grupo

```bash
curl -X POST "http://localhost:8080/groups/NOME_DO_GRUPO/members/remove" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sam_account_name": "usuario.teste",
    "confirm": true,
    "dry_run": true,
    "reason": "Chamado INC123456 aprovado pelo gestor"
  }'
```

## Grupo Protegido

```bash
curl -X POST "http://localhost:8080/groups/Domain%20Admins/members/add" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sam_account_name": "usuario.teste",
    "confirm": true,
    "dry_run": true,
    "protected_group_confirm": true,
    "reason": "Chamado CHG123456 aprovado pelo comite"
  }'
```

## Resposta

Cada operacao retorna:

- Operacao solicitada.
- Grupo alvo.
- Usuario alvo.
- DN do usuario.
- Se foi dry-run.
- Se houve mudanca real.
- Se o grupo foi considerado protegido.

## Cuidados

- Comece sempre com `dry_run=true`.
- Proteja grupos administrativos com fluxo de aprovacao.
- Use justificativa rastreavel no campo `reason`.
- Evite automacoes sem revisao humana em grupos privilegiados.
