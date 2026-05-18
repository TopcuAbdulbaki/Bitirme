param(
    [ValidateSet("start", "stop", "restart", "status", "supervise")]
    [string]$Action = "start",
    [ValidateSet("all", "orchestrator", "crawler")]
    [string]$Node = "all",
    [string]$ProjectRoot = "C:\Users\HP\Desktop\Projeler\Bitirme",
    [int]$RestartDelaySeconds = 5,
    [switch]$StopExisting,
    [switch]$Visible
)

$ErrorActionPreference = "Stop"

$RuntimeRoot = Join-Path $ProjectRoot ".runtime\local-nodes"
$OrchestratorLog = Join-Path $env:USERPROFILE "orchestrator.log"
$CrawlerLog = Join-Path $env:USERPROFILE "crawler.log"

function Write-Step([string]$Message) {
    Write-Host "[$(Get-Date -Format HH:mm:ss)] $Message" -ForegroundColor Cyan
}

function Test-Port([string]$HostName, [int]$Port, [int]$TimeoutMs = 1000) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Get-NodeList {
    if ($Node -eq "all") {
        return @("orchestrator", "crawler")
    }
    return @($Node)
}

function Get-SupervisorPidPath([string]$NodeName) {
    return Join-Path $RuntimeRoot "$NodeName.supervisor.pid"
}

function Get-ServiceProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -like "*\.venv-orch\Scripts\python.exe" -or
        $_.ExecutablePath -like "*\crawler\.venv\Scripts\python.exe" -or
        $_.CommandLine -like "*-m orchestrator.main*" -or
        $_.CommandLine -like "*-m crawler.main*" -or
        $_.CommandLine -like "*BITIRME_LOCAL_NODE=*"
    }
}

function Stop-LocalNodes {
    foreach ($nodeName in Get-NodeList) {
        $pidPath = Get-SupervisorPidPath $nodeName
        if (Test-Path -LiteralPath $pidPath) {
            $pidValue = (Get-Content -LiteralPath $pidPath -Raw).Trim()
            if ($pidValue) {
                Stop-Process -Id ([int]$pidValue) -Force -ErrorAction SilentlyContinue
            }
            Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
        }
    }

    $processes = @(Get-ServiceProcesses)
    foreach ($process in ($processes | Sort-Object ProcessId -Descending)) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Start-SupervisorWindow([string]$NodeName) {
    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null

    $args = @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-File", $PSCommandPath,
        "-Action", "supervise",
        "-Node", $NodeName,
        "-ProjectRoot", $ProjectRoot,
        "-RestartDelaySeconds", "$RestartDelaySeconds"
    )

    $windowStyle = if ($Visible) { "Normal" } else { "Hidden" }
    $proc = Start-Process -FilePath "pwsh.exe" -ArgumentList $args -WindowStyle $windowStyle -PassThru
    Set-Content -LiteralPath (Get-SupervisorPidPath $NodeName) -Value $proc.Id
    Write-Step "$NodeName supervisor visible window started pid=$($proc.Id)"
}

function Show-Status {
    $ports = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -in 50051, 8088, 5672 } |
        Select-Object LocalAddress, LocalPort, OwningProcess

    Write-Step "Listening ports"
    $ports | Format-Table -AutoSize

    Write-Step "Service processes"
    Get-ServiceProcesses | Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine | Format-Table -AutoSize

    Write-Step "Logs"
    Write-Host "orchestrator: $OrchestratorLog"
    Write-Host "crawler:      $CrawlerLog"
}

function Invoke-OrchestratorLoop {
    Set-Location $ProjectRoot
    $env:BITIRME_LOCAL_NODE = "orchestrator"
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONUNBUFFERED = "1"
    $env:GRPC_HOST = "0.0.0.0"
    $env:GRPC_PORT = "50051"
    $env:ORCHESTRATOR_HTTP_HOST = "127.0.0.1"
    $env:ORCHESTRATOR_HTTP_PORT = "8088"
    $env:RABBITMQ_HOST = "localhost"
    $env:RABBITMQ_PORT = "5672"
    $env:RABBITMQ_USER = "guest"
    $env:RABBITMQ_PASSWORD = "guest"
    $env:POSTGRES_HOST = "localhost"
    $env:POSTGRES_PORT = "5432"
    $env:POSTGRES_DB = "news_db"
    $env:POSTGRES_USER = "news_user"
    $env:POSTGRES_PASSWORD = "news_password"
    $env:ORCHESTRATOR_DB_HOST = "localhost"
    $env:ORCHESTRATOR_DB_PORT = "5432"
    $env:ORCHESTRATOR_DB_NAME = "news_db"
    $env:ORCHESTRATOR_DB_USER = "news_user"
    $env:ORCHESTRATOR_DB_PASSWORD = "news_password"
    $env:ORCHESTRATOR_SEARCH_EMBEDDING_MODE = "local"

    while ($true) {
        while (-not (Test-Port "127.0.0.1" 5672 1000)) {
            Write-Step "RabbitMQ 127.0.0.1:5672 not ready; waiting"
            Start-Sleep -Seconds 2
        }

        Remove-Item $OrchestratorLog -ErrorAction SilentlyContinue
        Write-Step "Starting orchestrator"
        .\.venv-orch\Scripts\python.exe -u -m orchestrator.main 2>&1 |
            Tee-Object -FilePath $OrchestratorLog -Append

        Write-Step "Orchestrator exited with code $LASTEXITCODE; restarting in ${RestartDelaySeconds}s"
        Start-Sleep -Seconds $RestartDelaySeconds
    }
}

function Invoke-CrawlerLoop {
    Set-Location $ProjectRoot
    $env:BITIRME_LOCAL_NODE = "crawler"
    $env:PYTHONPATH = $ProjectRoot
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONUNBUFFERED = "1"
    $env:CRAWLER_MODE = "distributed"
    $env:ORCHESTRATOR_HOST = "127.0.0.1"
    $env:ORCHESTRATOR_PORT = "50051"
    $env:POLL_INTERVAL = "5"
    $env:HEARTBEAT_INTERVAL = "10"
    $env:CRAWLER_DEMO_MODE = "false"

    while ($true) {
        while (-not (Test-Port "127.0.0.1" 50051 1000)) {
            Write-Step "Orchestrator gRPC 127.0.0.1:50051 not ready; waiting"
            Start-Sleep -Seconds 2
        }

        Remove-Item $CrawlerLog -ErrorAction SilentlyContinue
        Write-Step "Starting crawler"
        .\crawler\.venv\Scripts\python.exe -u -m crawler.main 2>&1 |
            Tee-Object -FilePath $CrawlerLog -Append

        Write-Step "Crawler exited with code $LASTEXITCODE; restarting in ${RestartDelaySeconds}s"
        Start-Sleep -Seconds $RestartDelaySeconds
    }
}

New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null

switch ($Action) {
    "start" {
        if ($StopExisting) {
            Stop-LocalNodes
            Start-Sleep -Seconds 2
        }
        foreach ($nodeName in Get-NodeList) {
            Start-SupervisorWindow $nodeName
            if ($nodeName -eq "orchestrator") {
                Start-Sleep -Seconds 3
            }
        }
        Show-Status
    }
    "restart" {
        Stop-LocalNodes
        Start-Sleep -Seconds 2
        foreach ($nodeName in Get-NodeList) {
            Start-SupervisorWindow $nodeName
            if ($nodeName -eq "orchestrator") {
                Start-Sleep -Seconds 3
            }
        }
        Show-Status
    }
    "stop" {
        Stop-LocalNodes
        Show-Status
    }
    "status" {
        Show-Status
    }
    "supervise" {
        if ($Node -eq "orchestrator") {
            Invoke-OrchestratorLoop
        } elseif ($Node -eq "crawler") {
            Invoke-CrawlerLoop
        } else {
            throw "supervise requires -Node orchestrator or -Node crawler"
        }
    }
}
