# CUA all-in-one Docker deployment script.
# Builds and runs one container that starts vLLM first, then CUA.

param(
    [ValidateSet("standalone", "node")]
    [string]$RunMode = "standalone",
    [string]$ImageName = "abdulbakitopcu/cua-allinone:latest",
    [string]$ContainerName = "cua-allinone",
    [string]$ModelId = "Qwen/Qwen3.5-9B",
    [int]$VllmPort = 1234,
    [string]$VllmApiKey = "lm-studio",
    [int]$MaxModelLen = 32768,
    [double]$GpuMemoryUtilization = 0.92,
    [int]$TensorParallelSize = 1,
    [string]$Query = "Turkey economy 2026",
    [int]$MaxArticles = 3,
    [int]$MaxCycles = 6,
    [string]$SearchEngine = "duckduckgo",
    [string]$OrchestratorHost = "",
    [int]$OrchestratorPort = 50051,
    [string]$RabbitMQHost = "",
    [int]$RabbitMQPort = 5672,
    [string]$RabbitMQUser = "guest",
    [string]$RabbitMQPassword = "guest"
)

$ErrorActionPreference = "Stop"

Write-Host "[CUA] Building all-in-one Docker image..." -ForegroundColor Cyan
docker build -t $ImageName -f cua/Dockerfile.allinone .

Write-Host "[CUA] Removing old container if exists..." -ForegroundColor Cyan
docker rm -f $ContainerName 2>$null | Out-Null

$envArgs = @(
    "-e", "CUA_RUN_MODE=$RunMode",
    "-e", "MODEL_ID=$ModelId",
    "-e", "MODEL_NAME=$ModelId",
    "-e", "VLLM_PORT=$VllmPort",
    "-e", "VLLM_API_KEY=$VllmApiKey",
    "-e", "LMSTUDIO_API_KEY=$VllmApiKey",
    "-e", "MAX_MODEL_LEN=$MaxModelLen",
    "-e", "GPU_MEMORY_UTILIZATION=$GpuMemoryUtilization",
    "-e", "TENSOR_PARALLEL_SIZE=$TensorParallelSize",
    "-e", "CUA_QUERY=$Query",
    "-e", "MAX_ARTICLES=$MaxArticles",
    "-e", "MAX_CYCLES=$MaxCycles",
    "-e", "SEARCH_ENGINE=$SearchEngine",
    "-e", "BROWSER_HEADLESS=true"
)

if ($RunMode -eq "node") {
    if (-not $OrchestratorHost -or -not $RabbitMQHost) {
        throw "Node mode requires -OrchestratorHost and -RabbitMQHost"
    }
    $envArgs += @(
        "-e", "ORCHESTRATOR_HOST=$OrchestratorHost",
        "-e", "ORCHESTRATOR_PORT=$OrchestratorPort",
        "-e", "RABBITMQ_HOST=$RabbitMQHost",
        "-e", "RABBITMQ_PORT=$RabbitMQPort",
        "-e", "RABBITMQ_USER=$RabbitMQUser",
        "-e", "RABBITMQ_PASSWORD=$RabbitMQPassword"
    )
}

Write-Host "[CUA] Starting all-in-one container..." -ForegroundColor Cyan
docker run `
    -d `
    --name $ContainerName `
    --gpus all `
    --network host `
    --ipc host `
    --shm-size 4g `
    --restart unless-stopped `
    -v "$env:USERPROFILE\.cache\huggingface:/models" `
    @envArgs `
    $ImageName

Write-Host "[CUA] Container started. Logs:" -ForegroundColor Green
docker logs -f $ContainerName
