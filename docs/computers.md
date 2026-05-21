# Consultas De Computadores

Esta etapa adiciona endpoints somente leitura para computadores do Active Directory.

## Permissao Necessaria

Os endpoints exigem token com a permissao:

```text
read:computers
```

Perfis com acesso:

- `viewer`
- `operator`
- `admin`
- `auditor`

## Listar Computadores

```bash
curl "http://localhost:8080/computers?status=active&limit=100" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Filtros disponiveis:

- `status=all`
- `status=active`
- `status=disabled`
- `status=inactive`
- `status=never_logged_on`
- `status=servers`
- `status=workstations`
- `status=domain_controllers`
- `status=old_machine_password`
- `status=missing_metadata`

Parametros opcionais:

- `query`: busca por CN, nome, DNS hostname, `sAMAccountName` ou sistema operacional.
- `ou_dn`: limita a busca a uma OU especifica.
- `operating_system`: filtra por sistema operacional.
- `inactive_days`: usado com `status=inactive`.
- `machine_password_days`: usado com `status=old_machine_password`.
- `limit`: limite de resultados, de 1 a 500.

## Buscar Computador

```bash
curl "http://localhost:8080/computers/NOME_DO_COMPUTADOR" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

O identificador pode ser:

- CN.
- Nome.
- DNS hostname.
- `sAMAccountName`.
- DN do computador.

## Campos Retornados

Cada computador retorna:

- DN.
- CN.
- Nome.
- DNS hostname.
- `sAMAccountName`.
- Descricao.
- Localizacao.
- Responsavel.
- Sistema operacional.
- Versao do sistema operacional.
- Service pack.
- Status habilitado/desabilitado.
- Indicador de servidor.
- Indicador de workstation.
- Indicador de controlador de dominio.
- Data de criacao.
- Data de alteracao.
- Ultimo logon conhecido.
- Data da ultima troca de senha da maquina.

## Observacoes

- Esta etapa nao altera contas de computador.
- Computadores obsoletos devem ser revisados manualmente antes de qualquer acao.
- `lastLogonTimestamp` pode ter atraso de replicacao no Active Directory.
- O filtro `old_machine_password` ajuda a identificar contas que podem estar sem rotacao recente de senha de maquina.
