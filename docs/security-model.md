# Modelo De Seguranca

Esta etapa adiciona autenticacao, autorizacao por perfil, correlation ID e auditoria estruturada.

## Perfis

Perfis iniciais:

- `viewer`: consultas e relatorios.
- `operator`: consultas, relatorios, teste de conexao AD e futuras operacoes controladas.
- `admin`: acesso administrativo completo.
- `auditor`: consultas, relatorios e leitura futura de auditoria.

## Token Inicial

O primeiro token de acesso e emitido usando `APP_BOOTSTRAP_ADMIN_TOKEN`, definido no `.env`.

Exemplo:

```bash
curl -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/json" \
  -H "X-Bootstrap-Token: $APP_BOOTSTRAP_ADMIN_TOKEN" \
  -d '{"subject":"admin.local","roles":["admin"]}'
```

A resposta contem um `access_token` assinado com `JWT_SECRET`.

## Login Pelo Active Directory

A interface web usa o endpoint:

```text
POST /auth/ad-login
```

O operador informa credenciais do AD. A API valida o bind LDAP/LDAPS do proprio usuario e, em seguida, consulta os grupos com a conta de servico configurada em `AD_BIND_DN`.

O perfil da aplicacao e definido pelos grupos do AD:

```env
AD_LOGIN_DOMAIN=tce.hml
AD_ROLE_ADMIN_GROUP_DN=CN=ADManager-Administradores,OU=Grupos,DC=tce,DC=hml
AD_ROLE_OPERATOR_GROUP_DN=CN=ADManager-Operadores,OU=Grupos,DC=tce,DC=hml
AD_ROLE_VIEWER_GROUP_DN=CN=ADManager-Leitores,OU=Grupos,DC=tce,DC=hml
AD_ROLE_AUDITOR_GROUP_DN=CN=ADManager-Auditores,OU=Grupos,DC=tce,DC=hml
```

Se o usuario autenticar no AD, mas nao pertencer a nenhum grupo mapeado, o acesso e negado. A verificacao considera grupos diretos e grupos aninhados do AD.

As operacoes no AD continuam sendo executadas pela conta de servico da aplicacao, que deve ter o menor privilegio necessario. Os grupos do usuario definem a autorizacao dentro da aplicacao e ficam registrados na auditoria.

## Usar Token

Use o token recebido no header `Authorization`:

```bash
curl http://localhost:8080/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Endpoints protegidos nesta fase:

- `GET /auth/me`
- `GET /config/summary`
- `GET /ad/connection-test`

## Auditoria

A API registra eventos estruturados em JSON para:

- Requisicoes HTTP.
- Emissao de token.
- Teste de conexao AD.

Cada resposta inclui:

```text
X-Correlation-ID
```

Se o cliente enviar `X-Correlation-ID`, a API preserva esse valor.

## Cuidados

- Nao compartilhe `APP_BOOTSTRAP_ADMIN_TOKEN`.
- Troque `APP_BOOTSTRAP_ADMIN_TOKEN` apos criar um fluxo real de usuarios.
- Nao use token `admin` para automacoes de rotina.
- Use o menor perfil necessario para cada operador.
- Mantenha `JWT_SECRET`, `SESSION_SECRET` e `ENCRYPTION_KEY` fora do Git.
