# CI E Deploy

Esta etapa adiciona pipeline de CI, build de imagens e base para deploy controlado.

## Pipeline

Arquivo:

```text
.github/workflows/ci.yml
```

Jobs:

- `api`: instala dependencias Python, valida sintaxe e roda testes.
- `frontend`: instala dependencias Node e gera build.
- `docker`: valida Compose e faz build das imagens.

Em tags `v*.*.*`, a pipeline publica imagens no GitHub Container Registry.

## Build Local

```bash
bash scripts/ci-local.sh
```

Ou manualmente:

```bash
docker compose build
```

## Publicacao Versionada

Crie uma tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

A pipeline publica:

```text
ghcr.io/OWNER/REPO/api:v0.1.0
ghcr.io/OWNER/REPO/worker:v0.1.0
ghcr.io/OWNER/REPO/frontend:v0.1.0
```

## Deploy

Use `compose.yaml` com `compose.prod.yaml`:

```bash
IMAGE_REGISTRY=ghcr.io \
IMAGE_NAMESPACE=owner/repo \
IMAGE_TAG=v0.1.0 \
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

## Variaveis De Ambiente

Cada ambiente deve ter seu proprio `.env`, fora do Git.

Obrigatorio revisar:

- `AD_SERVER`
- `AD_USE_LDAPS`
- `AD_TLS_REQUIRE_CERT`
- `AD_BIND_DN`
- `AD_BIND_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET`
- `SESSION_SECRET`
- `ENCRYPTION_KEY`
- `APP_BOOTSTRAP_ADMIN_TOKEN`

## Ordem Recomendada

1. Aplicar `.env` do ambiente.
2. Montar certificados em `docker/secrets`.
3. Subir banco e Redis.
4. Aplicar migrações.
5. Subir API.
6. Validar `/health`.
7. Validar `/ad/connection-test`.
8. Subir worker.
9. Subir frontend.
10. Executar teste de leitura e dry-run.

Para a rotina completa de prontidao, use [operations-runbook.md](operations-runbook.md).

## Rollback

Troque `IMAGE_TAG` para a versao anterior e reaplique:

```bash
IMAGE_TAG=v0.0.9 docker compose -f compose.yaml -f compose.prod.yaml up -d
```

Antes de rollback envolvendo banco, confirme se houve migracao irreversivel.
