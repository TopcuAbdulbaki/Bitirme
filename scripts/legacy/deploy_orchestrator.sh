#!/bin/bash
# 1. Update and install Docker (if not present)
sudo apt-get update
sudo apt-get install -y docker.io git

# 2. Start Docker service
sudo service docker start
sudo usermod -aG docker $USER

# 3. Pull Orchestrator
# (Make sure you pushed it from your PC first!)
sudo docker pull abdulbakitopcu/orchestrator:latest

# 4. Run Orchestrator
# Maps port 50051 (gRPC) and 5672 (RabbitMQ)
sudo docker run -d \
  --name orchestrator \
  --restart unless-stopped \
  -p 50051:50051 \
  -p 5672:5672 \
  abdulbakitopcu/orchestrator:latest
