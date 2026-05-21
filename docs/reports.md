# Relatorios

Esta etapa adiciona relatorios exportaveis em JSON e CSV para usuarios, grupos e computadores.

## Permissao Necessaria

Para gerar relatorios:

```text
run:reports
```

Para consultar historico:

```text
read:audit
```

## Relatorio De Usuarios

JSON:

```bash
curl "http://localhost:8080/reports/users?status=active&format=json&limit=1000" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

CSV:

```bash
curl "http://localhost:8080/reports/users?status=inactive&inactive_days=90&format=csv" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -o usuarios-inativos.csv
```

Filtros principais:

- `status`
- `query`
- `group_dn`
- `ou_dn`
- `inactive_days`
- `limit`

## Relatorio De Grupos

```bash
curl "http://localhost:8080/reports/groups?status=without_description&format=csv" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -o grupos-sem-descricao.csv
```

Filtros principais:

- `status`
- `query`
- `ou_dn`
- `limit`

## Relatorio De Computadores

```bash
curl "http://localhost:8080/reports/computers?status=old_machine_password&machine_password_days=90&format=csv" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -o computadores-senha-antiga.csv
```

Filtros principais:

- `status`
- `query`
- `ou_dn`
- `operating_system`
- `inactive_days`
- `machine_password_days`
- `limit`

## Historico

```bash
curl "http://localhost:8080/reports/history?limit=100" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

O historico e gravado em:

```text
reports/report-history.jsonl
```

Relatorios CSV tambem sao gravados no diretorio configurado por:

```env
REPORT_OUTPUT_DIR=/app/reports
```

## Observacoes

- Os relatorios reutilizam as consultas somente leitura ja protegidas por permissao.
- Arquivos CSV ficam no volume `reports`.
- O historico contem metadados da execucao, operador, filtros e quantidade de linhas.
- Senhas, tokens e segredos nao sao exportados.
