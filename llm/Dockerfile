# Dockerfile for LLM Node
# System Requirements: GPU (NVIDIA), 16GB+ VRAM
# Base Image: Python 3.11 Slim (Better ML compatibility)

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_MODE=local

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY llm/requirements.txt ./requirements.txt

# Install Python dependencies
# Large download
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY llm/ ./llm/
COPY proto/ ./proto/

# Compile proto files
# Compile proto files DIRECTLY into the generated folder
RUN python -m grpc_tools.protoc -Iproto --python_out=llm/generated --grpc_python_out=llm/generated orchestrator.proto

# Create non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Environment Variables
ENV GRPC_PORT=50055
ENV ORCHESTRATOR_HOST=orchestrator
ENV ORCHESTRATOR_PORT=50051

# Expose ports
EXPOSE 50055

# Run LLM Node
CMD ["python", "-m", "llm.main"]
