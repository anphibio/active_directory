# Conectividade Active Directory

Esta etapa prepara a aplicacao para validar configuracao e testar conexao LDAP/LDAPS com o Active Directory.

## Variaveis Obrigatorias

Para executar um teste real de conexao, preencha no `.env`:

```env
AD_DOMAIN=corp.example.local
AD_BASE_DN=DC=corp,DC=example,DC=local
AD_SERVER=ldaps://dc01.corp.example.local:636
AD_BIND_DN=CN=svc-ad-manager,OU=Service Accounts,DC=corp,DC=example,DC=local
AD_BIND_PASSWORD=change-me
AD_USE_LDAPS=true
AD_TLS_REQUIRE_CERT=true
AD_CA_CERT_PATH=/run/secrets/ad_ca_cert
```

## Certificado

Quando `AD_TLS_REQUIRE_CERT=true`, coloque o certificado da CA em:

```text
docker/secrets/ad_ca_cert
```

O arquivo sera montado no container em:

```text
/run/secrets/ad_ca_cert
```

## Validar Configuracao

Dentro do container da API:

```bash
docker compose run --rm api python -m app.validate_environment
```

O comando retorna:

- `0` quando as variaveis obrigatorias de AD estao preenchidas.
- `1` quando falta alguma variavel obrigatoria.

O resultado nao exibe senhas, tokens ou URLs sensiveis completas.

## Testar Conexao AD

Com a API em execucao:

```bash
curl http://localhost:8080/ad/connection-test
```

Possiveis status:

- `ok`: conexao e bind realizados com sucesso.
- `not_configured`: faltam variaveis obrigatorias no `.env`.
- `error`: houve falha de rede, TLS, DNS, credencial ou bind.

## Endpoints Disponiveis

- `GET /health`: saude basica da API.
- `GET /config/summary`: resumo seguro da configuracao.
- `GET /ad/connection-test`: teste de conexao e bind com AD.

## Cuidados

- Use LDAPS em ambientes reais.
- Nao use conta Domain Admin para bind.
- Garanta que a conta de servico tenha apenas as permissoes necessarias.
- Nunca registre `AD_BIND_PASSWORD` em logs.
- Valide certificados para evitar conexoes inseguras.
