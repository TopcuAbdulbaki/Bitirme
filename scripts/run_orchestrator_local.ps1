$ErrorActionPreference = "Stop"

Set-Location "C:\Users\HP\Desktop\Projeler\Bitirme"

$env:GRPC_HOST = "0.0.0.0"
$env:GRPC_PORT = "50051"
$env:ORCHESTRATOR_HTTP_HOST = "127.0.0.1"
$env:ORCHESTRATOR_HTTP_PORT = "8088"
$env:RABBITMQ_HOST = "localhost"
$env:RABBITMQ_PORT = "5672"
$env:RABBITMQ_USER = "guest"
$env:RABBITMQ_PASSWORD = "guest"

.\.venv-orch\Scripts\python.exe -m orchestrator.main
