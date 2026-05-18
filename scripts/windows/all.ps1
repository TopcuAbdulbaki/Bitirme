param(
    [string]$Config = "$PSScriptRoot\..\nodes.local.json",
    [switch]$DryRun,
    [switch]$Visible
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $Config)) {
    $Config = "$PSScriptRoot\..\nodes.example.json"
}

$cfg = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$defaults = $cfg.defaults
$nodes = @($cfg.nodes)

$localOrch = @($nodes | Where-Object { $_.role -eq "orchestrator" -and $_.run -eq "local" }).Count -gt 0
$localCrawler = @($nodes | Where-Object { $_.role -eq "crawler" -and $_.run -eq "local" }).Count -gt 0

if ($localOrch -and $localCrawler) {
    $orchParams = @{ Action = "start" }
    if ($DryRun) { $orchParams.DryRun = $true }
    if ($Visible) { $orchParams.Visible = $true }
    & "$PSScriptRoot\orch_and_crawler.ps1" @orchParams
}

foreach ($node in $nodes) {
    $role = [string]$node.role
    if ($localOrch -and $localCrawler -and ($role -eq "orchestrator" -or $role -eq "crawler")) {
        continue
    }

    $script = Join-Path $PSScriptRoot "$role.ps1"
    $run = if ($node.run) { [string]$node.run } elseif ($node.host) { "remote" } else { "local" }
    $sshUser = if ($node.sshUser) { [string]$node.sshUser } else { [string]$defaults.sshUser }
    $sshPort = if ($node.sshPort) { [int]$node.sshPort } else { [int]$defaults.sshPort }
    $targetOs = if ($node.targetOs) { [string]$node.targetOs } else { [string]$defaults.targetOs }

    $invokeParams = @{}
    if ($role -ne "orchestrator") {
        $invokeParams.OrchestratorHost = [string]$defaults.orchestratorHost
        $invokeParams.OrchestratorPort = [int]$defaults.orchestratorPort
        $invokeParams.RabbitMQHost = [string]$defaults.rabbitmqHost
        $invokeParams.RabbitMQPort = [int]$defaults.rabbitmqPort
    }
    if ($role -eq "db" -or $role -eq "vlm") {
        $invokeParams.MinioHost = [string]$defaults.minioHost
        $invokeParams.MinioPort = [int]$defaults.minioPort
    }
    if ($role -eq "db") {
        $invokeParams.PostgresHost = [string]$defaults.postgresHost
        $invokeParams.PostgresPort = [int]$defaults.postgresPort
    }
    if ($run -eq "local") {
        $invokeParams.Local = $true
    } else {
        $invokeParams.TargetHost = [string]$node.host
        $invokeParams.SshUser = $sshUser
        $invokeParams.SshPort = $sshPort
        $invokeParams.TargetOs = $targetOs
    }
    if ($DryRun) { $invokeParams.DryRun = $true }

    & $script @invokeParams
}
