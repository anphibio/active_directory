[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$Endpoint = $env:ADMANAGER_STATUS_ENDPOINT,

    [Parameter(Mandatory = $false)]
    [string]$Token = $env:ADMANAGER_WORKSTATION_TOKEN,

    [Parameter(Mandatory = $false)]
    [int]$TimeoutSec = 10,

    [Parameter(Mandatory = $false)]
    [int]$JitterMaxSeconds = 20
)

$ErrorActionPreference = "Stop"

function Test-ValidInteractiveUser {
    param(
        [Parameter(Mandatory = $false)]
        [string]$UserName
    )

    if ([string]::IsNullOrWhiteSpace($UserName)) {
        return $false
    }

    $account = $UserName
    if ($account -like "*\*") {
        $account = $account.Split("\")[-1]
    }

    if ($account.EndsWith("$")) {
        return $false
    }

    if ($account -match "^(DWM-|UMFD-|LOCAL SERVICE$|NETWORK SERVICE$|SYSTEM$)") {
        return $false
    }

    return $true
}

function Get-ActiveSessionIds {
    $activeSessionIds = @()
    $lockedSessionIds = @()

    try {
        $queryUserOutput = & query user 2>$null
    }
    catch {
        return $activeSessionIds
    }

    try {
        $lockedSessionIds = @(Get-CimInstance Win32_Process -Filter "name = 'LogonUI.exe'" |
            Select-Object -ExpandProperty SessionId -Unique)
    }
    catch {
        $lockedSessionIds = @()
    }

    foreach ($line in ($queryUserOutput | Select-Object -Skip 1)) {
        $normalizedLine = ($line -replace "^\s*>", "").Trim()
        if ([string]::IsNullOrWhiteSpace($normalizedLine)) {
            continue
        }

        $parts = $normalizedLine -split "\s+"
        $sessionId = $null
        $sessionState = $null

        for ($index = 1; $index -lt $parts.Count; $index++) {
            if ($parts[$index] -match "^\d+$") {
                $sessionId = [int]$parts[$index]
                if (($index + 1) -lt $parts.Count) {
                    $sessionState = $parts[$index + 1]
                }
                break
            }
        }

        if (
            $null -ne $sessionId -and
            $sessionState -match "^(Active|Ativo|Ativa)$" -and
            -not ($lockedSessionIds -contains $sessionId)
        ) {
            $activeSessionIds += $sessionId
        }
    }

    return $activeSessionIds | Select-Object -Unique
}

function Format-DomainUser {
    param(
        [Parameter(Mandatory = $false)]
        [string]$Domain,

        [Parameter(Mandatory = $false)]
        [string]$User
    )

    if ([string]::IsNullOrWhiteSpace($User)) {
        return $null
    }

    if ([string]::IsNullOrWhiteSpace($Domain)) {
        return $User
    }

    return "$Domain\$User"
}

function Get-InteractiveUser {
    $activeSessionIds = @(Get-ActiveSessionIds)
    if ($activeSessionIds.Count -eq 0) {
        return $null
    }

    $explorerOwner = Get-CimInstance Win32_Process -Filter "name = 'explorer.exe'" |
        Where-Object { $activeSessionIds -contains $_.SessionId } |
        ForEach-Object {
            try {
                $owner = Invoke-CimMethod -InputObject $_ -MethodName GetOwner
                if ($owner.ReturnValue -eq 0 -and (Test-ValidInteractiveUser $owner.User)) {
                    Format-DomainUser -Domain $owner.Domain -User $owner.User
                }
            }
            catch {
                $null
            }
        } |
        Where-Object { Test-ValidInteractiveUser $_ } |
        Select-Object -First 1

    if (Test-ValidInteractiveUser $explorerOwner) {
        return $explorerOwner
    }

    $computerSystemUser = (Get-CimInstance Win32_ComputerSystem).UserName
    if (Test-ValidInteractiveUser $computerSystemUser) {
        return $computerSystemUser
    }

    return $null
}

try {
    if ([string]::IsNullOrWhiteSpace($Endpoint) -or [string]::IsNullOrWhiteSpace($Token)) {
        exit 0
    }

    if ($JitterMaxSeconds -gt 0) {
        Start-Sleep -Seconds (Get-Random -Minimum 0 -Maximum $JitterMaxSeconds)
    }

    if ($PSVersionTable.PSVersion.Major -lt 6) {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    }

    $computer = $env:COMPUTERNAME
    $user = Get-InteractiveUser
    if (-not (Test-ValidInteractiveUser $user)) {
        exit 0
    }

    $ip = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object {
            $_.IPAddress -notlike "169.254*" -and
            $_.IPAddress -ne "127.0.0.1" -and
            $_.PrefixOrigin -ne "WellKnown" -and
            $_.AddressState -eq "Preferred"
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
        -TimeoutSec $TimeoutSec | Out-Null

    exit 0
}
catch {
    exit 0
}
