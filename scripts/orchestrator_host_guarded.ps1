param(
    [string]$ProjectRoot = "C:\Users\HP\Desktop\Projeler\Bitirme",
    [string]$PythonExe = "python",
    [string]$RabbitContainer = "rabbitmq",
    [string]$GrpcHost = "0.0.0.0",
    [int]$GrpcPort = 50051,
    [string]$HttpHost = "127.0.0.1",
    [int]$HttpPort = 8088,
    [string]$RabbitHost = "localhost",
    [int]$RabbitPort = 5672,
    [switch]$StartRabbitWithCompose,
    [switch]$StopExistingOrchestrator,
    [switch]$FollowLogs
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "[$(Get-Date -Format HH:mm:ss)] $Message" -ForegroundColor Cyan
}

function Fail([string]$Message) {
    throw $Message
}

Set-Location $ProjectRoot

if (-not (Test-Path "orchestrator\main.py")) {
    Fail "Project root is invalid: $ProjectRoot"
}

Write-Step "Waiting for RabbitMQ port $RabbitHost`:$RabbitPort"
$rabbitReady = $false
for ($i = 0; $i -lt 10; $i++) {
    if ((Test-NetConnection -ComputerName $RabbitHost -Port $RabbitPort -WarningAction SilentlyContinue).TcpTestSucceeded) {
        $rabbitReady = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $rabbitReady -and $StartRabbitWithCompose) {
    Write-Step "Starting RabbitMQ with docker compose"
    docker version --format '{{.Server.Version}}' | Out-Null
    docker compose up -d rabbitmq | Out-Host

    for ($i = 0; $i -lt 45; $i++) {
        if ((Test-NetConnection -ComputerName $RabbitHost -Port $RabbitPort -WarningAction SilentlyContinue).TcpTestSucceeded) {
            $rabbitReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }
}

if (-not $rabbitReady) {
    Fail "RabbitMQ did not become reachable on $RabbitHost`:$RabbitPort. Start it first, or re-run with -StartRabbitWithCompose."
}

if (-not (Test-Path ".venv-orch\Scripts\python.exe")) {
    Write-Step "Creating .venv-orch"
    & $PythonExe -m venv .venv-orch
}

Write-Step "Installing orchestrator requirements"
.\.venv-orch\Scripts\python.exe -m pip install -U pip setuptools wheel | Out-Host
.\.venv-orch\Scripts\python.exe -m pip install -r orchestrator\requirements.txt | Out-Host

Write-Step "Checking orchestrator imports"
.\.venv-orch\Scripts\python.exe -c "import orchestrator.main; import orchestrator.services.admin_http; print('orchestrator import ok')" | Out-Host

$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*-m orchestrator.main*"
}
if ($existing) {
    if ($StopExistingOrchestrator) {
        Write-Step "Stopping existing orchestrator process"
        $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
        Start-Sleep -Seconds 2
    } else {
        Fail "Existing orchestrator process detected. Re-run with -StopExistingOrchestrator to replace it."
    }
}

$logPath = Join-Path $env:USERPROFILE "orchestrator.log"
$pidPath = Join-Path $env:USERPROFILE "orchestrator.pid"
Remove-Item $logPath -ErrorAction SilentlyContinue

Write-Step "Starting orchestrator"
$launch = @"
`$env:GRPC_HOST='$GrpcHost'
`$env:GRPC_PORT='$GrpcPort'
`$env:ORCHESTRATOR_HTTP_HOST='$HttpHost'
`$env:ORCHESTRATOR_HTTP_PORT='$HttpPort'
`$env:RABBITMQ_HOST='$RabbitHost'
`$env:RABBITMQ_PORT='$RabbitPort'
`$env:RABBITMQ_USER='guest'
`$env:RABBITMQ_PASSWORD='guest'
Set-Location '$ProjectRoot'
.\.venv-orch\Scripts\python.exe -m orchestrator.main *>> '$logPath'
"@
$proc = Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $launch -WindowStyle Hidden -PassThru
$proc.Id | Set-Content $pidPath

Write-Step "Waiting for orchestrator readiness"
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
        if (Test-Path $logPath) { Get-Content $logPath -Tail 120 | Out-Host }
        Fail "Orchestrator exited during startup"
    }
    $grpcOk = (Test-NetConnection -ComputerName "127.0.0.1" -Port $GrpcPort -WarningAction SilentlyContinue).TcpTestSucceeded
    $httpOk = (Test-NetConnection -ComputerName "127.0.0.1" -Port $HttpPort -WarningAction SilentlyContinue).TcpTestSucceeded
    if ($grpcOk -and $httpOk) {
        $ready = $true
        break
    }
}
if (-not $ready) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    if (Test-Path $logPath) { Get-Content $logPath -Tail 120 | Out-Host }
    Fail "Orchestrator readiness timed out"
}

Write-Step "Orchestrator ready"
Write-Host "gRPC: http://$GrpcHost`:$GrpcPort"
Write-Host "Panel: http://$HttpHost`:$HttpPort"
Write-Host "PID: $($proc.Id)"
Write-Host "Log: $logPath"

if ($FollowLogs) {
    Get-Content $logPath -Wait
}
