# Operacoes Controladas Em Computadores

Esta etapa adiciona operacoes controladas para contas de computador do Active Directory.

## Permissao Necessaria

Todos os endpoints exigem:

```text
write:computers
```

Perfis com acesso nesta fase:

- `operator`
- `admin`

## Protecoes

Todas as operacoes exigem:

- Token valido.
- Permissao `write:computers`.
- `confirm=true`.
- `reason` com justificativa.
- Auditoria estruturada.
- `dry_run=true` por padrao.

## Habilitar Computador

```bash
curl -X POST "http://localhost:8080/computers/NOME-DO-PC/enable" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true,"dry_run":true,"reason":"Validacao operacional em modo simulado"}'
```

## Desabilitar Computador

```bash
curl -X POST "http://localhost:8080/computers/NOME-DO-PC/disable" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true,"dry_run":true,"reason":"Chamado INC123456 aprovado pelo responsavel"}'
```

## Atualizar Metadados

Campos permitidos:

- `description`
- `location`
- `managed_by`

```bash
curl -X POST "http://localhost:8080/computers/NOME-DO-PC/metadata" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirm": true,
    "dry_run": true,
    "reason": "Atualizacao de inventario conforme chamado INC123456",
    "description": "Notebook do setor financeiro",
    "location": "Sede - 2 andar",
    "managed_by": "CN=Usuario Responsavel,OU=Usuarios,DC=example,DC=local"
  }'
```

## Resposta

Cada operacao retorna:

- Operacao solicitada.
- Identificador usado.
- DN do computador.
- Se foi dry-run.
- Se houve mudanca real.
- Estado anterior.
- Estado posterior, quando houve alteracao real.

## Cuidados

- Comece sempre com `dry_run=true`.
- Nao desabilite computadores sem validar impacto operacional.
- Controladores de dominio devem ter fluxo separado de aprovacao e mudanca.
- Use justificativa rastreavel no campo `reason`.
- Para `managed_by`, informe um DN valido.
