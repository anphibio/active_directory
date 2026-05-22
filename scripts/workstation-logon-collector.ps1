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

    return -not $account.EndsWith("$")
}

function Get-InteractiveUser {
    $explorerOwner = Get-CimInstance Win32_Process -Filter "name = 'explorer.exe'" |
        ForEach-Object {
            try {
                $owner = Invoke-CimMethod -InputObject $_ -MethodName GetOwner
                if ($owner.ReturnValue -eq 0 -and (Test-ValidInteractiveUser $owner.User)) {
                    "$($owner.Domain)\$($owner.User)"
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

    $interactiveSessionUser = Get-CimInstance Win32_LogonSession -Filter "LogonType = 2 OR LogonType = 10" |
        ForEach-Object {
            try {
                Get-CimAssociatedInstance -InputObject $_ -Association Win32_LoggedOnUser |
                    ForEach-Object {
                        if (Test-ValidInteractiveUser $_.Name) {
                            "$($_.Domain)\$($_.Name)"
                        }
                    }
            }
            catch {
                $null
            }
        } |
        Where-Object { Test-ValidInteractiveUser $_ } |
        Select-Object -First 1

    return $interactiveSessionUser
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
