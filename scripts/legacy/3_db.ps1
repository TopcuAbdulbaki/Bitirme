# ============================================
# DB - Deploy Script
# ============================================

param(
    [string]$OrchHost,
    [string]$OrchPort = "50051"
)

# Load environment variables from .env
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            Set-Variable -Name $matches[1].Trim() -Value $matches[2].Trim() -Scope Script
        }
    }
}

# Use env vars if params not provided
if (-not $OrchHost -and $ORCH_HOST) { $OrchHost = $ORCH_HOST }
if (-not $OrchPort -or $OrchPort -eq "50051") { if ($ORCH_PORT) { $OrchPort = $ORCH_PORT } }

# Set defaults
if (-not $GH_TOKEN) { $GH_TOKEN = "<TOKEN>" }
if (-not $DOCKER_USER) { $DOCKER_USER = "abdulbakitopcu" }
if (-not $DOCKER_TOKEN) { $DOCKER_TOKEN = "<DOCKER_TOKEN>" }
if (-not $OrchHost) { Write-Host "ERROR: OrchHost required!" -ForegroundColor Red; exit 1 }

# DB credentials
$PgUser = "bitirme"
$PgPassword = "bitirme123"
$PgDb = "news_db"
$MinioUser = "minioadmin"
$MinioPassword = "minioadmin123"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "DB DEPLOYMENT" -ForegroundColor Cyan
Write-Host "Orchestrator: ${OrchHost}:${OrchPort}" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan

Write-Host "`n=== COPY-PASTE THIS ON VAST.AI DB ===" -ForegroundColor Green
Write-Host @"

# --- SYSTEM UPDATES ---
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
sudo service docker start
echo "$DOCKER_TOKEN" | sudo docker login -u $DOCKER_USER --password-stdin

# --- DATABASES (PostgreSQL + MinIO) ---
sudo docker network create db-net

sudo docker run -d --name postgres --network db-net -e POSTGRES_USER=$PgUser -e POSTGRES_PASSWORD=$PgPassword -e POSTGRES_DB=$PgDb -v postgres_data:/var/lib/postgresql/data pgvector/pgvector:pg15

sudo docker run -d --name minio --network db-net -e MINIO_ROOT_USER=$MinioUser -e MINIO_ROOT_PASSWORD=$MinioPassword minio/minio server /data

# --- DB SERVICE ---
git clone https://${GH_TOKEN}@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker build -f db/Dockerfile -t ${DOCKER_USER}/db:latest .
sudo docker push ${DOCKER_USER}/db:latest
sudo docker run -d --name db --network db-net --restart unless-stopped -e ORCHESTRATOR_HOST=${OrchHost} -e ORCHESTRATOR_PORT=${OrchPort} -e POSTGRES_HOST=postgres -e POSTGRES_PORT=5432 -e POSTGRES_USER=$PgUser -e POSTGRES_PASSWORD=$PgPassword -e POSTGRES_DB=$PgDb -e MINIO_HOST=minio -e MINIO_PORT=9000 -e MINIO_ACCESS_KEY=$MinioUser -e MINIO_SECRET_KEY=$MinioPassword ${DOCKER_USER}/db:latest
sudo docker logs db -f

"@
