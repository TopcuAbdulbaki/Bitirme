# Dockerfile for Crawler Node
# System Requirements: 2 CPU, 4GB RAM (Browser overhead)
# Base Image: Python 3.13 Slim

FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CRAWLER_MODE=distributed

# Set working directory
WORKDIR /app

# Install system dependencies
# - wget, gnupg: for Playwright browser downloads
# - netcat-openbsd: for healthchecks
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY crawler/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only to save space)
RUN playwright install-deps
RUN playwright install chromium

# Copy source code
COPY crawler/ ./crawler/
COPY proto/ ./proto/

# Compile proto files
# Compile proto files DIRECTLY into the generated folder (Overwriting old files)
# We use -Iproto to treat the proto folder as root, so it generates 'orchestrator_pb2.py' without 'proto/' prefix.
RUN python -m grpc_tools.protoc -Iproto --python_out=crawler/generated --grpc_python_out=crawler/generated orchestrator.proto

# Create non-root user (Disabled for Windows Build Speed)
# RUN useradd -m appuser && chown -R appuser /app
# USER appuser

# Environment Variables (Defaults)
ENV GRPC_PORT=50052
ENV ORCHESTRATOR_HOST=orchestrator
ENV ORCHESTRATOR_PORT=50051

# Expose ports
EXPOSE 50052

# Run Crawler (Server Mode)
CMD ["python", "-m", "crawler.main"]
