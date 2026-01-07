# Dockerfile for Database Node
# System Requirements: 2 CPU, 4GB RAM (due to local embeddings)
# Base Image: Python 3.13 Slim

FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
# - netcat-openbsd: for healthchecks
# - build-essential: for compiling some python extensions if needed
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY db/requirements.txt ./requirements.txt

# Install Python dependencies
# This step will take time due to torch/sentence-transformers
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY db/ ./db/
COPY proto/ ./proto/

# Compile proto files
# Compile proto files DIRECTLY into the generated folder
RUN python -m grpc_tools.protoc -Iproto --python_out=db/generated --grpc_python_out=db/generated orchestrator.proto

# Fix import in generated file (Python 3 relative import issue)
RUN sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' db/generated/orchestrator_pb2_grpc.py

# Create non-root user (Disabled for Windows Build Speed if needed, but standard practice)
# RUN useradd -m appuser && chown -R appuser /app
# USER appuser

# Environment Variables (Defaults)
ENV GRPC_PORT=50053
ENV POSTGRES_HOST=postgres
ENV POSTGRES_PORT=5432
ENV MINIO_HOST=minio
ENV MINIO_PORT=9000

# Expose ports
EXPOSE 50053

# Run DB Node
CMD ["python", "-m", "db.main"]
