# Coletor De Logon Das Estacoes

Esta etapa registra qual usuario esta ativo em cada estacao e permite exibir, na tela de usuarios, o ultimo computador informado pelo coletor.

O dado vem das estacoes via GPO e nao substitui o `lastLogonTimestamp` do Active Directory. Ele e um sinal operacional recente, util para suporte, auditoria e investigacao.

## Configuracao Da API

Defina no `.env`:

```env
WORKSTATION_STATUS_ENABLED=true
WORKSTATION_STATUS_TOKEN=troque-por-um-token-longo
```

O endpoint aceita:

- `POST /api/status`
- `POST /workstation-status`

O envio deve conter o cabecalho:

```text
X-Workstation-Token: <token configurado>
```

Em producao, use HTTPS e um token longo gerado para esta finalidade.

## Script PowerShell Para GPO

O script versionado esta em:

```text
scripts/workstation-logon-collector.ps1
```

Ele le o endpoint e o token de variaveis de ambiente da estacao:

```powershell
$env:ADMANAGER_STATUS_ENDPOINT = "https://SEU-SERVIDOR/api/status"
$env:ADMANAGER_WORKSTATION_TOKEN = "TOKEN_DA_GPO"
.\scripts\workstation-logon-collector.ps1
```

Tambem e possivel passar por parametro na Scheduled Task:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\\DOMINIO\SYSVOL\DOMINIO\scripts\workstation-logon-collector.ps1" -Endpoint "https://SEU-SERVIDOR/api/status" -Token "TOKEN_DA_GPO"
```

Modelo resumido do script:

```powershell
$ErrorActionPreference = "Stop"

$Endpoint = "https://SEU-SERVIDOR/api/status"
$Token = "TROQUE-PELO-TOKEN-DA-GPO"

try {
    Start-Sleep -Seconds (Get-Random -Minimum 0 -Maximum 20)

    $computer = $env:COMPUTERNAME
    $user = Get-InteractiveUser
    if (-not $user -or $user.EndsWith('$')) {
        exit 0
    }
    $ip = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object {
            $_.IPAddress -notlike "169.254*" -and
            $_.IPAddress -ne "127.0.0.1" -and
            $_.PrefixOrigin -ne "WellKnown"
        } |
        Select-Object -First 1 -ExpandProperty IPAddress

    $body = @{
        computer = $computer
        user = $user
        ip = $ip
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json -Compress

    Invoke-RestMethod `
        -Uri $Endpoint `
        -Method POST `
        -Headers @{ "X-Workstation-Token" = $Token } `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 10
}
catch {
    exit 0
}
```

O script versionado em `scripts/workstation-logon-collector.ps1` inclui a funcao `Get-InteractiveUser`.
Ela consulta as sessoes ativas do Windows com `query user`, usa apenas sessoes marcadas como
`Active`, `Ativo` ou `Ativa`, ignora sessoes com tela bloqueada detectada por `LogonUI.exe`, e so
entao identifica o dono do `explorer.exe` daquela sessao ou o usuario interativo atual em
`Win32_ComputerSystem.UserName`.

Se nao houver sessao ativa, se a sessao for historica/desconectada, ou se o resultado for uma conta
de maquina terminada em `$`, o script encerra sem enviar evento. Isso evita registrar falso positivo
quando a tarefa roda como `NT AUTHORITY\SYSTEM` e o Windows ainda possui sessoes antigas em WMI.

## Agendamento Por GPO

Recomendado:

- Executar como `SYSTEM`.
- Acionar no logon do usuario.
- Repetir a cada 5 minutos em ambientes normais.
- Usar 1 minuto somente quando houver necessidade operacional clara.
- Manter o atraso aleatorio do script para evitar muitas estacoes enviando ao mesmo tempo.

Se optar por 1 minuto, acompanhe uso da API, PostgreSQL e volume da tabela `workstation_status_events`.

## Retencao Dos Eventos

Configure por quanto tempo o historico do coletor deve ser mantido:

```env
WORKSTATION_STATUS_RETENTION_DAYS=90
WORKER_WORKSTATION_STATUS_RETENTION_ENABLED=true
WORKER_WORKSTATION_STATUS_RETENTION_INTERVAL_SECONDS=86400
```

O worker executa o job `workstation_status_retention` e remove somente registros antigos da tabela `workstation_status_events`.

## Consulta De Logons Recentes

Pelo frontend, use a guia **Logons** para pesquisar eventos recebidos pelo coletor por:

- usuario;
- computador;
- IP;
- periodo;
- limite de linhas.

Essa consulta e indicada para confirmar se um usuario especifico teve atividade em uma estacao em
um dia, sem depender do atraso normal do `lastLogonTimestamp` do Active Directory.

Pela API:

```bash
curl "http://localhost:8080/workstation-logons?user=usuario.teste&start=2026-05-20T00:00:00-03:00&end=2026-05-20T23:59:59-03:00&limit=100" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Configuracao Da GPO

### 1. Copiar O Script Para O SYSVOL

Copie o script para um caminho acessivel pelas estacoes, por exemplo:

```text
\\DOMINIO\SYSVOL\DOMINIO\scripts\workstation-logon-collector.ps1
```

Use o script versionado do projeto:

```text
scripts/workstation-logon-collector.ps1
```

Nao coloque o token dentro desse script quando ele for usado em producao.

### 2. Criar Ou Editar Uma GPO

No controlador de dominio:

1. Abra `Group Policy Management`.
2. Crie uma GPO, por exemplo `AD Manager - Coletor de Logon`.
3. Vincule primeiro a uma OU piloto com poucas estacoes.
4. Edite a GPO.

### 3. Criar A Scheduled Task

Dentro da edicao da GPO, acesse:

```text
Computer Configuration
Preferences
Control Panel Settings
Scheduled Tasks
```

Crie uma nova tarefa:

```text
New > Scheduled Task (At least Windows 7)
```

Na aba `General`:

- `Name`: `AD Manager - Coletor de Logon`
- `Run whether user is logged on or not`: habilitado
- `Run with highest privileges`: habilitado
- `User account`: `NT AUTHORITY\SYSTEM`
- `Configure for`: versao do Windows usada nas estacoes

Mesmo executando como `SYSTEM`, o script identifica o usuario interativo real. Se nenhum usuario
interativo valido estiver ativo, se houver apenas sessao desconectada ou tela bloqueada, ou se o
resultado for uma conta de maquina terminada em `$`, o script encerra sem enviar evento.

### 4. Configurar Os Triggers

Na aba `Triggers`, crie:

```text
Begin the task: At startup
```

E marque:

```text
Repeat task every: 5 minutes
for a duration of: Indefinitely
```

Para teste ou necessidade operacional especifica, use `1 minute`, mas monitore carga da API e crescimento da tabela.

Opcionalmente, adicione tambem um trigger:

```text
Begin the task: At log on
```

### 5. Configurar A Acao

Na aba `Actions`, crie uma acao:

```text
Action: Start a program
Program/script: powershell.exe
```

Em `Add arguments`, informe:

```text
-NoProfile -ExecutionPolicy Bypass -File "\\DOMINIO\SYSVOL\DOMINIO\scripts\workstation-logon-collector.ps1" -Endpoint "https://SEU-SERVIDOR/api/status" -Token "TOKEN_DA_GPO"
```

Substitua:

- `DOMINIO` pelo dominio real.
- `https://SEU-SERVIDOR/api/status` pela URL publicada da API.
- `TOKEN_DA_GPO` pelo mesmo valor de `WORKSTATION_STATUS_TOKEN` configurado na API.

### 6. Configurar Condicoes

Na aba `Conditions`, para estacoes corporativas normalmente faz sentido:

- Desmarcar `Start the task only if the computer is on AC power`, se houver notebooks.
- Manter a execucao dependente de rede, se a opcao estiver disponivel no ambiente.

### 7. Configurar Comportamento

Na aba `Settings`:

- Marque `Allow task to be run on demand`.
- Marque `Run task as soon as possible after a scheduled start is missed`.
- Configure `If the task is already running`: `Do not start a new instance`.
- Configure um tempo maximo de execucao, por exemplo `5 minutes`.

### 8. Aplicar E Testar

Em uma estacao piloto, atualize politicas:

```powershell
gpupdate /force
```

Confira se a tarefa foi criada em:

```text
Task Scheduler > Task Scheduler Library
```

Execute manualmente a tarefa e valide se a API recebeu o status.

### 9. Cuidados De Seguranca

- Trate o token como segredo operacional.
- Restrinja quem pode editar a GPO e ler o local onde o token aparece.
- Prefira HTTPS com certificado valido.
- Comece com uma OU piloto antes de aplicar em todas as estacoes.
- Rotacione o token se ele for exposto.

## Validacao

Teste manual em uma estacao:

```powershell
Invoke-RestMethod `
    -Uri "https://SEU-SERVIDOR/api/status" `
    -Method POST `
    -Headers @{ "X-Workstation-Token" = "TOKEN" } `
    -Body '{"computer":"PC-TESTE","user":"DOMINIO\usuario","ip":"10.0.0.10","timestamp":"2026-05-20T12:00:00Z"}' `
    -ContentType "application/json"
```

A resposta esperada e `status = ok`. Depois, abra a tela de usuarios e confira as colunas `Computador do logon` e `IP`.
