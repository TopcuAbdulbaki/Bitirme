# ============================================
# BUILD ALL - Run on Vast.ai Build Machine
# ============================================
# This is for building on Vast.ai (faster upload)

cd C:\Users\HP\Desktop\Projeler\Bitirme
git add .
git commit -m "Update for deployment"
git push origin master

Write-Host "Code pushed! Now run on Vast.ai Build Machine:" -ForegroundColor Green
Write-Host @"

# === PASTE THIS ON VAST.AI BUILD MACHINE ===
curl -fsSL https://get.docker.com | sh
sudo service docker start

# Clone (replace YOUR_TOKEN)
git clone https://github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme

# Login to Docker Hub
sudo docker login -u abdulbakitopcu (token)


# Build ALL
sudo docker build -f orchestrator/Dockerfile -t abdulbakitopcu/orchestrator:latest .
sudo docker build -f crawler/Dockerfile -t abdulbakitopcu/crawler:latest .
sudo docker build -f db/Dockerfile -t abdulbakitopcu/db:latest .
sudo docker build -f vlm/Dockerfile -t abdulbakitopcu/vlm:latest .
sudo docker build -f llm/Dockerfile -t abdulbakitopcu/llm:latest .

# Push ALL
sudo docker push abdulbakitopcu/orchestrator:latest
sudo docker push abdulbakitopcu/crawler:latest
sudo docker push abdulbakitopcu/db:latest
sudo docker push abdulbakitopcu/vlm:latest
sudo docker push abdulbakitopcu/llm:latest

echo "All images pushed!"

"@
