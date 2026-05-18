param(
    [Parameter(Mandatory = $true)][ValidateSet("orchestrator", "crawler", "db", "vlm", "llm", "cua")]
    [string]$Role,
    [string]$TargetHost = "",
    [string]$SshUser = "root",
    [int]$SshPort = 22,
    [ValidateSet("auto", "linux", "windows")]
    [string]$TargetOs = "auto",
    [switch]$Local,
    [switch]$DryRun,
    [switch]$Visible,
    [string]$OrchestratorHost = "",
    [int]$OrchestratorPort = 50051,
    [string]$RabbitMQHost = "",
    [int]$RabbitMQPort = 5672,
    [string]$PostgresHost = "",
    [int]$PostgresPort = 5432,
    [string]$MinioHost = "",
    [int]$MinioPort = 9000,
    [string[]]$PassThruArgs = @()
)

$ErrorActionPreference = "Stop"

$HelperRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptsRoot = Split-Path -Parent (Split-Path -Parent $HelperRoot)
$LinuxHelperRoot = Join-Path $ScriptsRoot "helper\linux"

function Get-LinuxHelperPath {
    param([string]$NodeRole)
    $map = @{
        orchestrator = "orchestrator.sh"
        crawler      = "crawler.sh"
        db           = "db.sh"
        vlm          = "vlm.sh"
        llm          = "llm.sh"
        cua          = "cua.sh"
    }
    return (Join-Path $LinuxHelperRoot $map[$NodeRole])
}

function Get-EndpointEnvPrefix {
    $pairs = @()
    if ($OrchestratorHost) { $pairs += "ORCHESTRATOR_HOST='$OrchestratorHost'" }
    $pairs += "ORCHESTRATOR_PORT='$OrchestratorPort'"
    if ($RabbitMQHost) { $pairs += "RABBITMQ_HOST='$RabbitMQHost'" }
    $pairs += "RABBITMQ_PORT='$RabbitMQPort'"
    if ($PostgresHost) { $pairs += "POSTGRES_HOST='$PostgresHost'" }
    $pairs += "POSTGRES_PORT='$PostgresPort'"
    if ($MinioHost) { $pairs += "MINIO_HOST='$MinioHost'" }
    $pairs += "MINIO_PORT='$MinioPort'"
    return ($pairs -join " ")
}

function Detect-RemoteOs {
    param([string]$Remote, [int]$Port)
    $detect = "if command -v uname >/dev/null 2>&1; then case `$(uname -s 2>/dev/null) in Linux*) printf linux; exit 0;; MINGW*|MSYS*|CYGWIN*) printf windows; exit 0;; esac; fi; if command -v pwsh >/dev/null 2>&1 || command -v powershell.exe >/dev/null 2>&1; then printf windows; exit 0; fi; printf unknown"
    return (& ssh -p $Port -o StrictHostKeyChecking=accept-new $Remote $detect).Trim()
}

function Invoke-LocalRole {
    if ($Role -eq "orchestrator") {
        $localScript = Join-Path $HelperRoot "orchestrator_local.ps1"
        if ($DryRun) {
            Write-Host "[dry-run] local role=orchestrator script=$localScript"
            return
        }
        & $localScript @PassThruArgs
        return
    }

    $helper = Get-LinuxHelperPath $Role
    if (-not (Test-Path -LiteralPath $helper)) {
        throw "Missing helper: $helper"
    }
    if ($DryRun) {
        Write-Host "[dry-run] local role=$Role helper=$helper via bash"
        return
    }
    $bash = Get-Command bash -ErrorAction SilentlyContinue
    if (-not $bash) {
        throw "Local $Role requires bash on this Windows machine, or use -TargetHost for remote Linux/Vast."
    }
    & $bash.Source $helper
}

if ($Local -or -not $TargetHost) {
    Invoke-LocalRole
    exit
}

$remote = "$SshUser@$TargetHost"
$detected = $TargetOs
if ($TargetOs -eq "auto" -and -not $DryRun) {
    $detected = Detect-RemoteOs -Remote $remote -Port $SshPort
}

$helperPath = Get-LinuxHelperPath $Role
if ($DryRun) {
    Write-Host "[dry-run] remote role=$Role target=$remote port=$SshPort target_os=$detected"
    Write-Host "[dry-run] would pipe $helperPath to remote bash with endpoint env"
    return
}

switch ($detected) {
    "linux" {
        $envPrefix = Get-EndpointEnvPrefix
        Get-Content -LiteralPath $helperPath -Raw | ssh -p $SshPort -o StrictHostKeyChecking=accept-new $remote "$envPrefix bash -s"
    }
    "windows" {
        throw "Windows target bootstrap for role '$Role' is not implemented as native install. Use a Linux/Vast target or run the matching script on the Windows target manually."
    }
    default {
        throw "Could not detect supported target OS for $remote. Detected: $detected"
    }
}
