# ============================================
# DB - Parameterized Deploy Script
# ============================================
# Usage: .\3_db.ps1 -OrchHost "116.102.85.223" -OrchPort "63567"

# Load environment variables from .env
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

param(
    [Parameter(Mandatory=$false)]
    [string]$Token = $env:GH_TOKEN,
    
    [Parameter(Mandatory=$false)]
    [string]$OrchHost = $env:ORCH_HOST,
    
    [Parameter(Mandatory=$false)]
    [string]$OrchPort = $env:ORCH_PORT,
    
    [Parameter(Mandatory=$false)]
    [string]$DockerUser = $env:DOCKER_USER,
    
    [Parameter(Mandatory=$false)]
    [string]$DockerToken = $env:DOCKER_TOKEN,
    
    [Parameter(Mandatory=$false)]
    [string]$PgUser = "bitirme",
    
    [Parameter(Mandatory=$false)]
    [string]$PgPassword = "bitirme123",
    
    [Parameter(Mandatory=$false)]
    [string]$PgDb = "news_db",
    
    [Parameter(Mandatory=$false)]
    [string]$MinioUser = "minioadmin",
    
    [Parameter(Mandatory=$false)]
    [string]$MinioPassword = "minioadmin123"
)

# Set defaults if not from env
if (-not $Token) { $Token = "<TOKEN>" }
if (-not $DockerUser) { $DockerUser = "abdulbakitopcu" }
if (-not $DockerToken) { $DockerToken = "<DOCKER_TOKEN>" }
if (-not $OrchHost) { Write-Host "ERROR: OrchHost required!" -ForegroundColor Red; exit 1 }

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "DB DEPLOYMENT" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

cd C:\Users\HP\Desktop\Projeler\Bitirme
git add .
git commit -m "Update"
git push origin master

Write-Host "`n=== COPY-PASTE THIS ON VAST.AI DB ===" -ForegroundColor Green
Write-Host @"

# --- SYSTEM UPDATES ---
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
sudo service docker start
echo "$DockerToken" | sudo docker login -u $DockerUser --password-stdin

# --- FRESH DEPLOY ---
sudo docker network create db-net

sudo docker run -d --name postgres \
  --network db-net \
  -e POSTGRES_USER=$PgUser \
  -e POSTGRES_PASSWORD=$PgPassword \
  -e POSTGRES_DB=$PgDb \
  -v postgres_data:/var/lib/postgresql/data \
  pgvector/pgvector:pg15

sudo docker run -d --name minio \
  --network db-net \
  -e MINIO_ROOT_USER=$MinioUser \
  -e MINIO_ROOT_PASSWORD=$MinioPassword \
  minio/minio server /data

git clone https://$Token@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker build -f db/Dockerfile -t $DockerUser/db:latest .
sudo docker push $DockerUser/db:latest
sudo docker run -d --name db \
  --network db-net \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=$OrchHost \
  -e ORCHESTRATOR_PORT=$OrchPort \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_USER=$PgUser \
  -e POSTGRES_PASSWORD=$PgPassword \
  -e POSTGRES_DB=$PgDb \
  -e MINIO_HOST=minio \
  -e MINIO_PORT=9000 \
  -e MINIO_ACCESS_KEY=$MinioUser \
  -e MINIO_SECRET_KEY=$MinioPassword \
  $DockerUser/db:latest
sudo docker logs db -f

# --- UPDATE (PostgreSQL & MinIO stay running!) ---
cd ~/Bitirme
git pull origin master
sudo docker build -f db/Dockerfile -t $DockerUser/db:latest .
sudo docker push $DockerUser/db:latest
sudo docker rm -f db
sudo docker run -d --name db \
  --network db-net \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=$OrchHost \
  -e ORCHESTRATOR_PORT=$OrchPort \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_USER=$PgUser \
  -e POSTGRES_PASSWORD=$PgPassword \
  -e POSTGRES_DB=$PgDb \
  -e MINIO_HOST=minio \
  -e MINIO_PORT=9000 \
  -e MINIO_ACCESS_KEY=$MinioUser \
  -e MINIO_SECRET_KEY=$MinioPassword \
  $DockerUser/db:latest
sudo docker logs db -f

"@
