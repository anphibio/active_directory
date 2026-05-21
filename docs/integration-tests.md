# Testes De Integracao

Esta etapa define como validar o sistema contra um Active Directory de laboratorio.

## Pre-requisitos

- `.env` preenchido.
- Conta de servico com permissoes minimas.
- Acesso de rede ao controlador de dominio.
- `ldapsearch` instalado no host ou container de teste.
- Ambiente de laboratorio separado de producao para testes de escrita.

## Validar `.env`

```bash
python3 scripts/validate-env.py
```

## Validar Bind LDAP/LDAPS

```bash
bash scripts/check-ldap.sh
```

O script nao imprime DN completo, senha ou objetos retornados.

## Validar API Local

Com a API em execucao:

```bash
bash scripts/check-api.sh
```

## Validacao Operacional Integrada

Para executar uma verificacao unica de prontidao:

```bash
bash scripts/operational-readiness.sh
```

Por padrao, o script valida:

- `.env`.
- Sintaxe Python.
- Build do frontend.
- `docker compose config`.
- Health da API.
- Emissao de token admin via `APP_BOOTSTRAP_ADMIN_TOKEN`.
- Endpoints protegidos principais.
- Metricas da API.
- Health e metricas do worker, quando disponiveis.
- Frontend, quando disponivel.
- Presenca de backup PostgreSQL em `backups/postgres`, quando ja houver backup.

Checks opcionais:

```bash
RUN_LDAP_CHECK=true bash scripts/operational-readiness.sh
```

```bash
RUN_DRY_RUN_CHECKS=true \
LAB_USER=usuario.teste \
LAB_COMPUTER=PC-TESTE \
bash scripts/operational-readiness.sh
```

Para validar apenas artefatos locais, sem Docker ou API:

```bash
RUN_DOCKER=false RUN_API_CHECKS=false bash scripts/operational-readiness.sh
```

Para ignorar temporariamente o check de backup:

```bash
RUN_BACKUP_CHECK=false bash scripts/operational-readiness.sh
```

## Testes De Leitura Recomendados

1. Emitir token com perfil `viewer`.
2. Consultar usuarios ativos.
3. Consultar grupos.
4. Consultar computadores.
5. Gerar relatorio JSON.
6. Gerar relatorio CSV.

## Testes De Escrita Em Laboratorio

Execute apenas com objetos de teste:

- Usuario temporario.
- Grupo temporario.
- Computador temporario.

Fluxo:

1. Executar com `dry_run=true`.
2. Conferir auditoria.
3. Executar com `dry_run=false`.
4. Validar resultado no AD.
5. Reverter a mudanca.
6. Conferir auditoria novamente.

## O Que Nao Fazer

- Nao testar escrita em grupos administrativos reais.
- Nao resetar senha de usuarios reais.
- Nao desabilitar computador de producao.
- Nao usar conta Domain Admin como conta da aplicacao.
