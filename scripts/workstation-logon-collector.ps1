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
    $user = (Get-CimInstance Win32_ComputerSystem).UserName
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
