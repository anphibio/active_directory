# Consultas De Usuarios

Esta etapa adiciona endpoints somente leitura para usuarios do Active Directory.

## Permissao Necessaria

Os endpoints exigem token com a permissao:

```text
read:users
```

Perfis com acesso nesta fase:

- `viewer`
- `operator`
- `admin`
- `auditor`

## Listar Usuarios

```bash
curl "http://localhost:8080/users?status=active&limit=100" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Filtros disponiveis:

- `status=all`
- `status=active`
- `status=disabled`
- `status=locked`
- `status=inactive`
- `status=never_logged_on`
- `status=password_never_expires`

Parametros opcionais:

- `query`: busca por `sAMAccountName`, UPN, nome de exibicao ou email.
- `group_dn`: filtra usuarios membros de um grupo.
- `ou_dn`: limita a busca a uma OU.
- `inactive_days`: usado com `status=inactive`.
- `limit`: limite de resultados, de 1 a 500.

Exemplos:

```bash
curl "http://localhost:8080/users?status=inactive&inactive_days=90" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

```bash
curl "http://localhost:8080/users?query=anderson" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Buscar Usuario Por Login

```bash
curl "http://localhost:8080/users/usuario.teste" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Campos Retornados

Cada usuario retorna:

- DN.
- `sAMAccountName`.
- UPN.
- Nome de exibicao.
- Email.
- Departamento.
- Cargo.
- Gerente.
- Status habilitado/desabilitado.
- Status bloqueado.
- Indicador de senha nunca expira.
- Data de criacao.
- Data de alteracao.
- Ultimo logon conhecido.
- Data da ultima troca de senha.

## Observacoes

- Esta etapa nao altera usuarios.
- Operacoes de senha, bloqueio, grupo e OU ficam para etapas posteriores.
- `lastLogonTimestamp` pode ter atraso de replicacao no Active Directory.
- Os filtros escapam caracteres especiais LDAP para reduzir risco de injecao em consulta.
