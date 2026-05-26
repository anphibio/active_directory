# Deploy Em Producao

Este guia descreve como publicar o Active Directory Manager em um host Docker de producao, com LDAPS, banco persistente, auditoria, worker e frontend.

Use este fluxo junto com:

- [production-checklist.md](production-checklist.md)
- [operations-runbook.md](operations-runbook.md)
- [backup-restore.md](backup-restore.md)
- [hardening.md](hardening.md)

## Modelo Recomendado

Em producao, prefira:

- host Linux dedicado ou VM corporativa;
- Docker Engine e Docker Compose Plugin;
- `.env` fora do Git;
- LDAPS com validacao TLS;
- certificado da CA do AD montado em `docker/secrets/ad_ca_cert`;
- PostgreSQL e Redis com volumes persistentes;
- frontend publicado por HTTPS via proxy corporativo ou balanceador;
- API e `/metrics` restritos por rede interna;
- backup externo do PostgreSQL.

## Preparar O Host

No servidor de producao:

```bash
sudo mkdir -p /opt/admanager
sudo chown "$USER":"$USER" /opt/admanager
cd /opt/admanager
```

Baixe o codigo:

```bash
git clone git@github.com:anphibio/active_directory.git .
```

Crie os diretorios operacionais:

```bash
mkdir -p docker/secrets reports backups/postgres
chmod 700 docker/secrets
```

## Configurar O `.env`

Crie o arquivo local:

```bash
cp .env.example .env
chmod 600 .env
```

Edite os valores reais. Em producao, revise obrigatoriamente:

```env
APP_ENV=production
APP_PORT=8080
APP_BASE_URL=https://admanager.seudominio.gov.br
CORS_ALLOWED_ORIGINS=https://admanager.seudominio.gov.br

AD_DOMAIN=tce.hml
AD_BASE_DN=DC=tce,DC=hml
AD_SERVER=ldaps://dc01.tce.hml:636
AD_BIND_DN=CN=svc-ad-manager,OU=Contas de Servico,DC=tce,DC=hml
AD_BIND_PASSWORD=senha-forte
AD_LOGIN_DOMAIN=tce.hml

AD_USE_LDAPS=true
AD_TLS_REQUIRE_CERT=true
AD_CA_CERT_PATH=/run/secrets/ad_ca_cert
ALLOW_INSECURE_LDAP_IN_PRODUCTION=false
REQUIRE_LDAPS_FOR_WRITES=true

AD_ROLE_ADMIN_GROUP_DN=CN=Administradores,OU=AD_Manager,OU=Grupos,DC=tce,DC=hml
AD_ROLE_OPERATOR_GROUP_DN=CN=Operadores,OU=AD_Manager,OU=Grupos,DC=tce,DC=hml
AD_ROLE_VIEWER_GROUP_DN=CN=Leitores,OU=AD_Manager,OU=Grupos,DC=tce,DC=hml
AD_ROLE_AUDITOR_GROUP_DN=CN=Auditores,OU=AD_Manager,OU=Grupos,DC=tce,DC=hml

POSTGRES_DB=admanager
POSTGRES_USER=admanager
POSTGRES_PASSWORD=senha-forte
DATABASE_URL=postgresql://admanager:senha-forte@database:5432/admanager

JWT_SECRET=valor-longo-aleatorio
SESSION_SECRET=valor-longo-aleatorio
ENCRYPTION_KEY=valor-longo-aleatorio
APP_BOOTSTRAP_ADMIN_TOKEN=valor-longo-aleatorio
WORKSTATION_STATUS_TOKEN=valor-longo-aleatorio

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=senha-forte
```

Gere segredos longos com uma ferramenta local aprovada pela sua politica. Exemplo:

```bash
openssl rand -base64 48
```

Nao reutilize a senha do PostgreSQL em `JWT_SECRET`, `SESSION_SECRET`, `ENCRYPTION_KEY`, token de bootstrap ou token do coletor.

## Configurar O Certificado Da CA Do AD

O arquivo abaixo deve conter a CA que emitiu o certificado LDAPS do controlador de dominio:

```text
docker/secrets/ad_ca_cert
```

Ele deve estar em formato PEM, parecido com:

```text
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
```

Permissoes recomendadas:

```bash
chmod 600 docker/secrets/ad_ca_cert
```

Valide o certificado contra o DC:

```bash
docker compose run --rm api openssl s_client \
  -connect dc01.tce.hml:636 \
  -CAfile /run/secrets/ad_ca_cert \
  -verify_return_error
```

O resultado esperado deve indicar `Verify return code: 0 (ok)`.

## Validar Antes De Subir

Execute:

```bash
python3 scripts/validate-env.py
docker compose config --quiet
```

Se o host tiver acesso ao AD, valide LDAP/LDAPS:

```bash
RUN_LDAP_CHECK=true bash scripts/operational-readiness.sh
```

## Subir Com Build Local

Este modo e simples para uma primeira implantacao ou ambiente controlado em que o servidor faz o build das imagens:

```bash
docker compose up -d --build database redis
docker compose run --rm api python -m app.migrate
docker compose up -d --build api worker frontend
```

Monitoramento:

```bash
docker compose --profile monitoring up -d --build prometheus alertmanager grafana
```

## Subir Com Imagens Versionadas

Quando houver imagens publicadas em registry, use `compose.prod.yaml` para nao fazer build no servidor:

```bash
IMAGE_REGISTRY=ghcr.io \
IMAGE_NAMESPACE=anphibio/active_directory \
IMAGE_TAG=v0.1.0 \
docker compose -f compose.yaml -f compose.prod.yaml up -d database redis

IMAGE_REGISTRY=ghcr.io \
IMAGE_NAMESPACE=anphibio/active_directory \
IMAGE_TAG=v0.1.0 \
docker compose -f compose.yaml -f compose.prod.yaml run --rm api python -m app.migrate

IMAGE_REGISTRY=ghcr.io \
IMAGE_NAMESPACE=anphibio/active_directory \
IMAGE_TAG=v0.1.0 \
docker compose -f compose.yaml -f compose.prod.yaml up -d api worker frontend
```

Se o registry for privado, autentique antes:

```bash
docker login ghcr.io
```

## Validar Depois De Subir

Confira containers e health checks:

```bash
docker compose ps
curl -fsS http://localhost:8080/health
curl -fsS http://localhost:9100/health
```

Valide a prontidao integrada:

```bash
RUN_LDAP_CHECK=true bash scripts/operational-readiness.sh
```

Depois, acesse o frontend pela URL publicada e valide:

- login com usuario do AD;
- perfil carregado conforme grupo do AD;
- consultas de usuarios, grupos e computadores;
- relatorio em CSV/PDF;
- operacao sensivel em modo `Simular`;
- auditoria aparecendo na guia `Logs`;
- coletor de estacao recebendo eventos na guia `Logons`.

## Publicacao Por HTTPS

O Compose atual expõe API e frontend em portas locais. Em producao, publique preferencialmente por proxy reverso corporativo.

O arquivo de referencia fica em:

```text
docker/nginx/admanager.conf
```

A regra esperada e:

- `/` aponta para `frontend:3000`;
- `/api/` aponta para `api:8080`;
- `/metrics` fica restrito a rede interna ou Prometheus.

O `APP_BASE_URL` e o `CORS_ALLOWED_ORIGINS` devem usar a URL HTTPS final, nao `localhost`.

## Atualizar Uma Versao Em Producao

Antes de atualizar:

```bash
git fetch --all
git status
bash scripts/backup-postgres.sh
```

Com build local:

```bash
git pull --ff-only
docker compose build api worker frontend
docker compose run --rm api python -m app.migrate
docker compose up -d api worker frontend
docker compose ps
```

Com imagem versionada:

```bash
IMAGE_TAG=v0.1.1 docker compose -f compose.yaml -f compose.prod.yaml pull api worker frontend
IMAGE_TAG=v0.1.1 docker compose -f compose.yaml -f compose.prod.yaml run --rm api python -m app.migrate
IMAGE_TAG=v0.1.1 docker compose -f compose.yaml -f compose.prod.yaml up -d api worker frontend
```

Quando alterar apenas `.env`, recrie os servicos que usam as variaveis:

```bash
docker compose up -d --force-recreate api worker frontend
```

Se alterar apenas o script do coletor de estacao, copie o novo `scripts/workstation-logon-collector.ps1` para o SYSVOL/GPO. Nao e necessario reiniciar a aplicacao.

## Backup E Restore

Antes de operacao real e antes de toda atualizacao:

```bash
bash scripts/backup-postgres.sh
```

O restore deve ser testado em ambiente isolado:

```bash
CONFIRM_RESTORE=true bash scripts/restore-postgres.sh backups/postgres/arquivo.sql.gz
```

Consulte [backup-restore.md](backup-restore.md).

## Rollback

Rollback com build local:

```bash
git checkout <commit-ou-tag-anterior>
docker compose build api worker frontend
docker compose up -d api worker frontend
```

Rollback com imagem versionada:

```bash
IMAGE_TAG=v0.1.0 docker compose -f compose.yaml -f compose.prod.yaml up -d api worker frontend
```

Antes de rollback envolvendo banco, confirme se a versao nova aplicou migracao incompativel. Se precisar restaurar banco, siga o procedimento de restore em ambiente controlado.

## Checklist De Liberacao

Liberar para operadores somente quando:

- `APP_ENV=production`;
- `AD_SERVER=ldaps://...:636`;
- `AD_USE_LDAPS=true`;
- `AD_TLS_REQUIRE_CERT=true`;
- `REQUIRE_LDAPS_FOR_WRITES=true`;
- certificado da CA validado;
- banco com backup recente;
- `scripts/operational-readiness.sh` sem falhas criticas;
- login AD validado;
- RBAC por grupos do AD validado;
- operacoes reais testadas primeiro em laboratorio;
- monitoramento ativo ou plano de observabilidade aprovado.
