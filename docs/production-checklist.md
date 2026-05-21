# Checklist De Producao

Use este checklist antes de liberar o sistema para operacao real.

Para a sequencia operacional completa, consulte [operations-runbook.md](operations-runbook.md).

## LDAPS

- LDAPS funcionando na porta `636`.
- Certificado do controlador de dominio valido.
- Certificado com Server Authentication.
- Cadeia da CA confiavel montada em `docker/secrets/ad_ca_cert`.
- `AD_USE_LDAPS=true`.
- `AD_TLS_REQUIRE_CERT=true`.
- Teste `GET /ad/connection-test` com sucesso.

## Conta De Servico

- Conta dedicada para a aplicacao.
- Senha forte e rotacao definida.
- Sem uso de Domain Admin.
- Permissoes delegadas apenas nas OUs necessarias.
- Permissoes de leitura para relatorios.
- Permissoes de escrita separadas e revisadas.
- Logon interativo bloqueado, quando aplicavel.

## Segredos

- `.env` fora do Git.
- `JWT_SECRET`, `SESSION_SECRET`, `ENCRYPTION_KEY` fortes.
- `APP_BOOTSTRAP_ADMIN_TOKEN` forte e rotacionado apos setup inicial.
- Backups de segredos em cofre corporativo.
- Secrets nao aparecem em logs.

## Banco E Auditoria

- PostgreSQL com volume persistente.
- Migrações aplicadas.
- Backup configurado.
- Restore testado.
- Retencao de auditoria definida.
- Consulta `/audit/events` validada.

## Docker

- Containers rodando sem root sempre que possivel.
- Volumes revisados.
- Health checks funcionando.
- Logs coletados pela plataforma.
- Porta da API protegida por rede ou proxy.
- Frontend publicado apenas no escopo necessario.

## Operacao

- Runbook de incidentes criado.
- Operadores treinados em `dry_run`.
- Fluxo de aprovacao para grupos protegidos.
- Procedimento de rollback validado.
- Ambiente de laboratorio mantido para testes.
- `bash scripts/operational-readiness.sh` executado sem falhas criticas.
- Checks opcionais de LDAP e dry-run executados em laboratorio antes da liberacao.
