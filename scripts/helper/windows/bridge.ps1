param(
    [ValidateSet("start", "stop", "restart", "status", "supervise")]
    [string]$Action = "status",
    [string]$ConfigPath = "",
    [string]$Node = "",
    [switch]$Visible
)

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$HelperRoot = Split-Path -Parent $ScriptRoot
$ScriptsRoot = Split-Path -Parent $HelperRoot
$RepoRoot = Split-Path -Parent $ScriptsRoot
$RuntimeRoot = Join-Path $RepoRoot ".runtime\node-bridges"
$DefaultLocalConfig = Join-Path $ScriptsRoot "node_bridges.local.json"
$DefaultExampleConfig = Join-Path $ScriptsRoot "node_bridges.example.json"

function Resolve-ConfigPath {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        return (Resolve-Path -LiteralPath $RequestedPath).Path
    }
    if (Test-Path -LiteralPath $DefaultLocalConfig) {
        return (Resolve-Path -LiteralPath $DefaultLocalConfig).Path
    }
    return (Resolve-Path -LiteralPath $DefaultExampleConfig).Path
}

function Read-BridgeConfig {
    param([string]$Path)

    $config = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    if (-not $config.nodes -or $config.nodes.Count -eq 0) {
        throw "Bridge config has no nodes: $Path"
    }
    return $config
}

function Get-ConfigValue {
    param(
        [object]$NodeConfig,
        [object]$Defaults,
        [string]$Name
    )

    $nodeProp = $NodeConfig.PSObject.Properties[$Name]
    if ($nodeProp -and $null -ne $nodeProp.Value -and "$($nodeProp.Value)" -ne "") {
        return $nodeProp.Value
    }

    $defaultProp = $Defaults.PSObject.Properties[$Name]
    if ($defaultProp -and $null -ne $defaultProp.Value -and "$($defaultProp.Value)" -ne "") {
        return $defaultProp.Value
    }

    throw "Missing bridge config value: $Name"
}

function Get-SelectedNodes {
    param(
        [object]$Config,
        [string]$NodeName
    )

    $nodes = @($Config.nodes)
    if (-not $NodeName) {
        return $nodes
    }

    $matched = @($nodes | Where-Object { $_.name -eq $NodeName })
    if ($matched.Count -eq 0) {
        throw "Unknown node '$NodeName' in bridge config."
    }
    return $matched
}

function Get-NodeSlug {
    param([object]$NodeConfig)
    return "$($NodeConfig.name)".ToLowerInvariant()
}

function Get-PidFile {
    param([object]$NodeConfig)
    return Join-Path $RuntimeRoot ("{0}.supervisor.pid" -f (Get-NodeSlug $NodeConfig))
}

function Get-StopFile {
    param([object]$NodeConfig)
    return Join-Path $RuntimeRoot ("{0}.stop" -f (Get-NodeSlug $NodeConfig))
}

function Get-LogFile {
    param([object]$NodeConfig)
    return Join-Path $RuntimeRoot ("{0}.log" -f (Get-NodeSlug $NodeConfig))
}

function Write-BridgeLog {
    param(
        [object]$NodeConfig,
        [string]$Message
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[{0}] [{1}] {2}" -f $timestamp, (Get-NodeSlug $NodeConfig), $Message
    $line | Tee-Object -FilePath (Get-LogFile $NodeConfig) -Append
}

function Get-LiveProcess {
    param([string]$PidFile)

    if (-not (Test-Path -LiteralPath $PidFile)) {
        return $null
    }

    $rawPid = (Get-Content -LiteralPath $PidFile -Raw).Trim()
    if (-not $rawPid) {
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
        return $null
    }

    $process = Get-Process -Id ([int]$rawPid) -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
        return $null
    }
    return $process
}

function New-SshArguments {
    param(
        [object]$NodeConfig,
        [object]$Defaults
    )

    $sshPort = [int](Get-ConfigValue $NodeConfig $Defaults "sshPort")
    $vastHost = [string](Get-ConfigValue $NodeConfig $Defaults "host")
    $localUiPort = [int](Get-ConfigValue $NodeConfig $Defaults "localUiPort")
    $nodeGrpcPort = [int](Get-ConfigValue $NodeConfig $Defaults "nodeGrpcPort")
    $nodeRabbitPort = [int](Get-ConfigValue $NodeConfig $Defaults "nodeRabbitPort")
    $localGrpcPort = [int](Get-ConfigValue $NodeConfig $Defaults "localGrpcPort")
    $localRabbitPort = [int](Get-ConfigValue $NodeConfig $Defaults "localRabbitPort")

    $args = @(
        "-p", "$sshPort",
        "-N",
        "-T",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "-o", "TCPKeepAlive=yes",
        "-L", "$localUiPort`:127.0.0.1:8080",
        "-R", "$nodeGrpcPort`:127.0.0.1:$localGrpcPort",
        "-R", "$nodeRabbitPort`:127.0.0.1:$localRabbitPort"
    )

    if ([bool]$NodeConfig.includeStoragePorts) {
        $nodePostgresPort = [int](Get-ConfigValue $NodeConfig $Defaults "nodePostgresPort")
        $nodeMinioPort = [int](Get-ConfigValue $NodeConfig $Defaults "nodeMinioPort")
        $localPostgresPort = [int](Get-ConfigValue $NodeConfig $Defaults "localPostgresPort")
        $localMinioPort = [int](Get-ConfigValue $NodeConfig $Defaults "localMinioPort")
        $args += @(
            "-R", "$nodePostgresPort`:127.0.0.1:$localPostgresPort",
            "-R", "$nodeMinioPort`:127.0.0.1:$localMinioPort"
        )
    }

    $args += "root@$vastHost"
    return ,$args
}

function Get-ForwardSummary {
    param(
        [object]$NodeConfig,
        [object]$Defaults
    )

    $nodeGrpcPort = Get-ConfigValue $NodeConfig $Defaults "nodeGrpcPort"
    $nodeRabbitPort = Get-ConfigValue $NodeConfig $Defaults "nodeRabbitPort"
    $localUiPort = Get-ConfigValue $NodeConfig $Defaults "localUiPort"
    $summary = "grpc=$nodeGrpcPort rabbit=$nodeRabbitPort local-ui=$localUiPort"
    if ([bool]$NodeConfig.includeStoragePorts) {
        $summary += " postgres=$(Get-ConfigValue $NodeConfig $Defaults "nodePostgresPort") minio=$(Get-ConfigValue $NodeConfig $Defaults "nodeMinioPort")"
    }
    return $summary
}

function Start-Supervisor {
    param(
        [object]$NodeConfig,
        [string]$ResolvedConfigPath,
        [switch]$ShowWindow
    )

    $pidFile = Get-PidFile $NodeConfig
    $existing = Get-LiveProcess $pidFile
    if ($existing) {
        Write-Host ("[{0}] supervisor already running pid={1}" -f (Get-NodeSlug $NodeConfig), $existing.Id)
        return
    }

    Remove-Item -LiteralPath (Get-StopFile $NodeConfig) -Force -ErrorAction SilentlyContinue

    $psArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $PSCommandPath,
        "-Action", "supervise",
        "-ConfigPath", $ResolvedConfigPath,
        "-Node", (Get-NodeSlug $NodeConfig)
    )

    $process = Start-Process -FilePath "pwsh.exe" `
        -ArgumentList $psArgs `
        -PassThru `
        -WindowStyle ($(if ($ShowWindow) { "Normal" } else { "Hidden" }))

    Set-Content -LiteralPath $pidFile -Value $process.Id
    Write-Host ("[{0}] supervisor started pid={1}; {2}" -f (Get-NodeSlug $NodeConfig), $process.Id, (Get-ForwardSummary $NodeConfig $config.defaults))
}

function Stop-Supervisor {
    param([object]$NodeConfig)

    $pidFile = Get-PidFile $NodeConfig
    $stopFile = Get-StopFile $NodeConfig
    Set-Content -LiteralPath $stopFile -Value (Get-Date -Format o)

    $existing = Get-LiveProcess $pidFile
    if ($existing) {
        Stop-Process -Id $existing.Id -Force
        Write-Host ("[{0}] supervisor stopped pid={1}" -f (Get-NodeSlug $NodeConfig), $existing.Id)
    } else {
        Write-Host ("[{0}] supervisor is not running" -f (Get-NodeSlug $NodeConfig))
    }

    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

function Show-Status {
    param([object]$NodeConfig)

    $existing = Get-LiveProcess (Get-PidFile $NodeConfig)
    $state = if ($existing) { "RUNNING pid=$($existing.Id)" } else { "STOPPED" }
    $logFile = Get-LogFile $NodeConfig
    Write-Host ("[{0}] {1}; {2}; log={3}" -f (Get-NodeSlug $NodeConfig), $state, (Get-ForwardSummary $NodeConfig $config.defaults), $logFile)
}

function Run-SupervisorLoop {
    param(
        [object]$NodeConfig,
        [object]$Defaults
    )

    $stopFile = Get-StopFile $NodeConfig
    $delay = [int](Get-ConfigValue $NodeConfig $Defaults "reconnectDelaySeconds")
    $sshArgs = New-SshArguments $NodeConfig $Defaults
    Write-BridgeLog $NodeConfig ("supervisor active; {0}" -f (Get-ForwardSummary $NodeConfig $Defaults))

    while (-not (Test-Path -LiteralPath $stopFile)) {
        Write-BridgeLog $NodeConfig ("starting ssh bridge to {0}:{1}" -f (Get-ConfigValue $NodeConfig $Defaults "host"), (Get-ConfigValue $NodeConfig $Defaults "sshPort"))
        & ssh.exe @sshArgs 2>&1 | ForEach-Object {
            Write-BridgeLog $NodeConfig $_
        }
        $exitCode = $LASTEXITCODE
        if (Test-Path -LiteralPath $stopFile) {
            break
        }
        Write-BridgeLog $NodeConfig ("ssh bridge exited with code {0}; retrying in {1}s" -f $exitCode, $delay)
        Start-Sleep -Seconds $delay
    }

    Write-BridgeLog $NodeConfig "supervisor stopped"
}

New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
$resolvedConfigPath = Resolve-ConfigPath $ConfigPath
$config = Read-BridgeConfig $resolvedConfigPath
$selectedNodes = Get-SelectedNodes $config $Node

switch ($Action) {
    "start" {
        foreach ($nodeConfig in $selectedNodes) {
            Start-Supervisor $nodeConfig $resolvedConfigPath -ShowWindow:$Visible
        }
    }
    "stop" {
        foreach ($nodeConfig in $selectedNodes) {
            Stop-Supervisor $nodeConfig
        }
    }
    "restart" {
        foreach ($nodeConfig in $selectedNodes) {
            Stop-Supervisor $nodeConfig
            Start-Supervisor $nodeConfig $resolvedConfigPath -ShowWindow:$Visible
        }
    }
    "status" {
        foreach ($nodeConfig in $selectedNodes) {
            Show-Status $nodeConfig
        }
    }
    "supervise" {
        if ($selectedNodes.Count -ne 1) {
            throw "Supervisor mode requires exactly one -Node."
        }
        Run-SupervisorLoop $selectedNodes[0] $config.defaults
    }
}
