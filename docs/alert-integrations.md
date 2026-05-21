# Integracoes Corporativas De Alertas

O Alertmanager e configurado por variaveis do `.env`. Por padrao, nenhum alerta externo e enviado.

## Webhook Generico

Use quando houver um relay corporativo, ITSM, automacao, Teams bridge ou Slack bridge preparado para receber o payload nativo do Alertmanager.

```env
ALERTMANAGER_WEBHOOK_ENABLED=true
ALERTMANAGER_WEBHOOK_URL=https://monitoramento.example.local/admanager-alerts
ALERTMANAGER_WEBHOOK_SEND_RESOLVED=true
```

Observacao: Microsoft Teams normalmente exige um adaptador entre Alertmanager e Teams. O webhook nativo do Teams nao interpreta diretamente o payload padrao do Alertmanager.

## E-Mail SMTP

```env
ALERTMANAGER_SMTP_ENABLED=true
ALERTMANAGER_SMTP_SMARTHOST=smtp.example.local:587
ALERTMANAGER_SMTP_FROM=admanager@example.local
ALERTMANAGER_SMTP_TO=infra@example.local
ALERTMANAGER_SMTP_AUTH_USERNAME=svc-admanager-alerts
ALERTMANAGER_SMTP_AUTH_PASSWORD=change-me
ALERTMANAGER_SMTP_REQUIRE_TLS=true
ALERTMANAGER_EMAIL_SEND_RESOLVED=true
```

## Severidades

Severidades iniciais:

- `critical`: API indisponivel ou falha de persistencia de auditoria.
- `warning`: worker indisponivel, erro HTTP 5xx ou falha em job.
- `info`: operacao sensivel executada/simulada ou ausencia recente de teste AD.

Alertas `critical` repetem em intervalo menor que os demais.

## Responsaveis Sugeridos

- `critical`: time de infraestrutura/AD com acionamento imediato.
- `warning`: time de infraestrutura durante janela operacional.
- `info`: revisao em rotina diaria ou semanal.

## Aplicar Alteracoes

Depois de alterar `.env`, recrie o Alertmanager:

```bash
docker compose --profile monitoring up -d --build alertmanager
```

Valide:

```bash
curl http://localhost:9093/-/ready
```
