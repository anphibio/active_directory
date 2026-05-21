# Operacoes Sensíveis Em Usuarios

Esta etapa adiciona operacoes controladas em usuarios do Active Directory.

## Permissao Necessaria

Todos os endpoints exigem:

```text
write:users
```

Perfis com acesso nesta fase:

- `operator`
- `admin`

## Protecoes

Todas as operacoes exigem:

- Token valido.
- Permissao `write:users`.
- `confirm=true`.
- `reason` com justificativa.
- Auditoria estruturada.

Por padrao, `dry_run=true`. Assim a API valida o alvo e registra a simulacao sem alterar o AD.

Para executar de verdade:

```json
{
  "confirm": true,
  "dry_run": false,
  "reason": "Chamado INC123456 aprovado pelo gestor"
}
```

## Habilitar Usuario

```bash
curl -X POST "http://localhost:8080/users/usuario.teste/enable" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true,"dry_run":true,"reason":"Validacao operacional em modo simulado"}'
```

## Desabilitar Usuario

```bash
curl -X POST "http://localhost:8080/users/usuario.teste/disable" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true,"dry_run":true,"reason":"Validacao operacional em modo simulado"}'
```

## Desbloquear Usuario

```bash
curl -X POST "http://localhost:8080/users/usuario.teste/unlock" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true,"dry_run":true,"reason":"Validacao operacional em modo simulado"}'
```

## Forcar Troca De Senha No Proximo Logon

```bash
curl -X POST "http://localhost:8080/users/usuario.teste/force-password-change" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true,"dry_run":true,"reason":"Validacao operacional em modo simulado"}'
```

## Resetar Senha

Reset de senha exige LDAPS quando `dry_run=false`.

```bash
curl -X POST "http://localhost:8080/users/usuario.teste/reset-password" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirm": true,
    "dry_run": true,
    "reason": "Validacao operacional em modo simulado",
    "new_password": "SenhaTemporariaForte@123",
    "force_change_at_next_logon": true
  }'
```

No ambiente atual com LDAP simples em `389`, a API permite apenas `dry_run=true` para reset de senha. Para executar de verdade, corrija LDAPS e use:

```env
AD_SERVER=ldaps://servidor:636
AD_USE_LDAPS=true
AD_TLS_REQUIRE_CERT=true
```

## Alterar Expiracao Da Conta

Use `never_expires=true` para deixar a conta sem data de expiracao:

```bash
curl -X POST "http://localhost:8080/users/usuario.teste/account-expiration" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirm": true,
    "dry_run": true,
    "reason": "Validacao operacional em modo simulado",
    "never_expires": true
  }'
```

Use `never_expires=false` e `expires_at` para definir uma data:

```bash
curl -X POST "http://localhost:8080/users/usuario.teste/account-expiration" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirm": true,
    "dry_run": true,
    "reason": "Validacao operacional em modo simulado",
    "never_expires": false,
    "expires_at": "2026-06-19T23:59:59-03:00"
  }'
```

No frontend, a operacao **Alterar expiracao da conta** primeiro carrega a configuracao atual do
usuario e so depois habilita os campos para simular uma nova data.

## Resposta

Cada operacao retorna:

- Operacao solicitada.
- Usuario alvo.
- DN do usuario.
- Se foi dry-run.
- Se houve mudanca real.
- Estado anterior.
- Estado posterior, quando houve alteracao real.

## Cuidados

- Comece sempre com `dry_run=true`.
- Nunca registre senha em chamados, logs ou prints.
- Use uma conta de servico com menor privilegio possivel.
- Nao execute reset de senha real sem LDAPS.
- Use uma justificativa rastreavel no campo `reason`.
