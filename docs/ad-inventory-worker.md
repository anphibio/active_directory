# Inventario AD Agendado

O worker coleta inventario real do Active Directory pela API interna.

## Como Funciona

1. O worker gera um token tecnico local assinado com `JWT_SECRET`.
2. Com perfil `auditor`, consulta endpoints de usuarios, grupos e computadores.
3. Gera um snapshot versionado em JSON.
4. Atualiza `inventory-snapshot-latest.json`.
5. Expoe o ultimo snapshot pela API em `/reports/inventory-snapshot`.
6. Expoe metricas agregadas no endpoint `/metrics` do worker.

## Variaveis

```env
WORKER_API_BASE_URL=http://api:8080
WORKER_API_SUBJECT=admanager-worker
WORKER_API_TIMEOUT_SECONDS=30
WORKER_API_TOKEN_MODE=local
WORKER_API_TOKEN_EXPIRE_SECONDS=3600
WORKER_INVENTORY_SNAPSHOT_ENABLED=true
WORKER_INVENTORY_SNAPSHOT_INTERVAL_SECONDS=86400
WORKER_INVENTORY_QUERY_LIMIT=500
WORKER_INVENTORY_INACTIVE_DAYS=90
WORKER_INVENTORY_MACHINE_PASSWORD_DAYS=90
WORKER_INVENTORY_USER_OUS=
WORKER_INVENTORY_GROUP_OUS=
WORKER_INVENTORY_COMPUTER_OUS=
```

Para segmentar por mais de uma OU, use `|` como separador:

```env
WORKER_INVENTORY_USER_OUS=OU=Users,DC=corp,DC=local|OU=Admins,DC=corp,DC=local
WORKER_INVENTORY_GROUP_OUS=OU=Groups,DC=corp,DC=local
WORKER_INVENTORY_COMPUTER_OUS=OU=Workstations,DC=corp,DC=local|OU=Servers,DC=corp,DC=local
```

## Arquivos

```text
reports/inventory-snapshot-YYYYMMDDHHMMSS.json
reports/inventory-snapshot-latest.json
```

## API

O ultimo snapshot pode ser consultado por usuarios com permissao de relatorios:

```bash
curl "http://localhost:8080/reports/inventory-snapshot" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Esse endpoint e usado pelo painel operacional do frontend.

## Metricas

```text
admanager_inventory_snapshot_timestamp
admanager_inventory_objects{object_type="users",status="active"}
admanager_inventory_query_capped{object_type="computers",status="inactive"}
admanager_inventory_query_errors{object_type="users",status="all"}
admanager_inventory_segment_objects{object_type="users",segment="OU=Users,DC=corp,DC=local",status="active"}
admanager_inventory_delta_objects{object_type="users",status="all"}
```

## Validacao

Depois de recriar o worker:

```bash
docker compose up -d --build worker
docker compose logs -f worker
curl http://localhost:9100/metrics
```

Verifique se existem metricas iniciando com:

```text
admanager_inventory_
```

## Cuidados

- O inventario usa apenas endpoints de leitura.
- O limite padrao por consulta e `500`.
- Se `capped=true`, aumente `WORKER_INVENTORY_QUERY_LIMIT` ou crie consultas segmentadas por OU em uma etapa futura.
- Se houver falha LDAP/API, o snapshot ainda e gravado com `error` na consulta afetada e a metrica `admanager_inventory_query_errors` fica maior que zero.
- Quando OUs forem configuradas, o snapshot passa a incluir a chave `segments`.
- A chave `delta_from_previous` mostra a diferenca de contagem entre o snapshot atual e o anterior.
- O token tecnico depende de `JWT_SECRET` igual entre API e worker.
- Para voltar ao fluxo via `/auth/token`, configure `WORKER_API_TOKEN_MODE=bootstrap`.
