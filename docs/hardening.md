# Hardening De Producao

Esta etapa adiciona controles para reduzir risco em producao.

## Controles De LDAP

Variaveis:

```env
AD_USE_LDAPS=true
AD_TLS_REQUIRE_CERT=true
ALLOW_INSECURE_LDAP_IN_PRODUCTION=false
REQUIRE_LDAPS_FOR_WRITES=true
```

Regras:

- Em `APP_ENV=production`, LDAP simples e bloqueado por padrao.
- Escritas reais exigem LDAPS quando `REQUIRE_LDAPS_FOR_WRITES=true`.
- `dry_run=true` continua permitido para validacao segura.
- LDAPS em producao deve validar certificado.

## Validacao De Prontidao

```bash
docker compose run --rm api python -m app.validate_environment
```

O comando retorna erro se:

- Produção estiver sem LDAPS.
- Produção estiver com LDAPS sem validacao de certificado.
- Auditoria persistente estiver desabilitada.

## Proxy Reverso

Exemplo base:

```text
docker/nginx/admanager.conf
```

Recomendacoes:

- Publicar frontend e API atras de TLS.
- Expor `/metrics` somente para rede interna ou Prometheus.
- Aplicar allowlist de rede para endpoints administrativos.
- Registrar logs de acesso no proxy.

## Prometheus E Grafana

Coleta:

```text
GET /metrics
```

Indicadores recomendados:

- Requisicoes por status.
- Latencia por rota.
- Eventos de auditoria por tipo.
- Falhas de LDAP.
- Falhas de jobs.

## Retencao

Defina politicas para:

- `audit_events`
- arquivos CSV em `reports`
- `worker-jobs.jsonl`
- backups do PostgreSQL

## Checklist Minimo

- `APP_ENV=production`.
- `AD_USE_LDAPS=true`.
- `AD_TLS_REQUIRE_CERT=true`.
- Certificado CA montado.
- Conta de servico sem Domain Admin.
- Segredos fortes.
- Auditoria persistente habilitada.
- Backup e restore testados.
- `/metrics` restrito por rede.
