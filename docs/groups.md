# Consultas De Grupos

Esta etapa adiciona endpoints somente leitura para grupos do Active Directory.

## Permissao Necessaria

Os endpoints exigem token com a permissao:

```text
read:groups
```

Perfis com acesso:

- `viewer`
- `operator`
- `admin`
- `auditor`

## Listar Grupos

```bash
curl "http://localhost:8080/groups?status=all&limit=100" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Filtros disponiveis:

- `status=all`
- `status=empty`
- `status=with_members`
- `status=without_description`
- `status=without_owner`

Parametros opcionais:

- `query`: busca por `cn`, `name`, `sAMAccountName` ou descricao.
- `ou_dn`: limita a busca a uma OU.
- `limit`: limite de resultados, de 1 a 500.

## Buscar Grupo

```bash
curl "http://localhost:8080/groups/NOME_DO_GRUPO" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

O identificador pode ser:

- `cn`
- `name`
- `sAMAccountName`
- DN do grupo

## Listar Membros De Um Grupo

```bash
curl "http://localhost:8080/groups/NOME_DO_GRUPO/members?limit=100" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

No frontend, use a guia **Grupos** e a area **Membros de um grupo** para pesquisar o grupo
por nome, `sAMAccountName` ou descricao e listar seus membros diretos.

## Listar Grupos De Um Usuario

```bash
curl "http://localhost:8080/groups/by-user/usuario.teste?include_nested=true&limit=500" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

O identificador aceita `sAMAccountName`, UPN ou DN do usuario. Por padrao, a API inclui grupos
diretos e grupos aninhados resolvidos pelo Active Directory.

## Campos Retornados

Grupos:

- DN.
- CN.
- Nome.
- `sAMAccountName`.
- Descricao.
- Email.
- Responsavel.
- Quantidade de membros.
- Tipo do grupo.
- Data de criacao.
- Data de alteracao.

Membros:

- DN.
- Classes do objeto.
- `sAMAccountName`.
- Nome de exibicao.
- CN.
- Email.

## Observacoes

- Esta etapa nao altera grupos.
- Operacoes de adicionar e remover usuarios de grupos ficam para etapa posterior.
- A contagem de membros usa o atributo `member` retornado pelo AD.
- Grupos muito grandes podem exigir paginacao/range retrieval em etapa futura.
