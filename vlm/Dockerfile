# Dockerfile for VLM Node
# System Requirements: GPU (NVIDIA), 24GB+ VRAM
# Base Image: Python 3.11 Slim (Better ML compatibility than 3.13)

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_MODE=transformers \
    PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=10

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY vlm/requirements.txt ./requirements.txt

# Install Python dependencies
# Large download (~4GB)
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY vlm/ ./vlm/
COPY proto/ ./proto/

# Compile proto files
# Compile proto files DIRECTLY into the generated folder
RUN python -m grpc_tools.protoc -Iproto --python_out=vlm/generated --grpc_python_out=vlm/generated orchestrator.proto

# Fix import in generated file (Python 3 relative import issue)
RUN sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' vlm/generated/orchestrator_pb2_grpc.py

# Create non-root user (Standard practice, can disable if permission issues arise)
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Environment Variables (Defaults)
ENV GRPC_PORT=50054
ENV ORCHESTRATOR_HOST=orchestrator
ENV ORCHESTRATOR_PORT=50051

# Expose ports
EXPOSE 50054

# Run VLM Node
CMD ["python", "-m", "vlm.main"]
