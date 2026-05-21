# Variaveis De Ambiente

Todas as configuracoes sensiveis devem ser fornecidas por `.env`, Docker secrets ou cofre corporativo.

## Arquivos

- `.env.example`: exemplo versionado, sem segredos reais.
- `.env`: configuracao local, ignorada pelo Git.
- `docker/secrets/`: arquivos sensiveis locais, ignorados pelo Git.

## Regras

- Nunca commitar `.env`.
- Nunca commitar senhas reais.
- Nunca registrar secrets em logs.
- Preferir LDAPS em ambientes reais.
- Validar certificados do controlador de dominio.

## Certificado AD

Quando `AD_TLS_REQUIRE_CERT=true`, monte o certificado da CA em:

```text
docker/secrets/ad_ca_cert
```

E referencie:

```env
AD_CA_CERT_PATH=/run/secrets/ad_ca_cert
```

## Frontend

Quando a interface web acessar a API pelo navegador, configure as origens permitidas:

```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:4173,http://127.0.0.1:4173
```

Em producao, use apenas as URLs oficiais da interface web.

## Coletor De Logon Das Estacoes

Para receber status das estacoes via GPO:

```env
WORKSTATION_STATUS_ENABLED=true
WORKSTATION_STATUS_TOKEN=troque-por-um-token-longo
```

Use um token exclusivo para esse coletor e envie pelo cabecalho `X-Workstation-Token`.
O guia completo esta em [workstation-logon-collector.md](workstation-logon-collector.md).

## Login AD E Perfis

Configure o dominio usado quando o operador digitar apenas o login curto:

```env
AD_LOGIN_DOMAIN=tce.hml
```

Configure os grupos do AD que concedem perfil na aplicacao:

```env
AD_ROLE_ADMIN_GROUP_DN=CN=ADManager-Administradores,OU=Grupos,DC=tce,DC=hml
AD_ROLE_OPERATOR_GROUP_DN=CN=ADManager-Operadores,OU=Grupos,DC=tce,DC=hml
AD_ROLE_VIEWER_GROUP_DN=CN=ADManager-Leitores,OU=Grupos,DC=tce,DC=hml
AD_ROLE_AUDITOR_GROUP_DN=CN=ADManager-Auditores,OU=Grupos,DC=tce,DC=hml
```

Os DNs devem apontar para grupos reais do Active Directory.
