# Dockerfile for Orchestrator Node
# System Requirements: 1 CPU, 2GB RAM
# Base Image: Python 3.13 Slim (Matches project version)

FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - netcat-openbsd: used for healthchecks (optional but good)
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY orchestrator/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
# We copy the specific service folder and the shared proto folder
COPY orchestrator/ ./orchestrator/
COPY proto/ ./proto/

# Helper script to compile protos
# We need to compile protos inside the container to ensure version compatibility
# Compile proto files DIRECTLY into the generated folder
RUN python -m grpc_tools.protoc -Iproto --python_out=orchestrator/generated --grpc_python_out=orchestrator/generated orchestrator.proto

# Fix import in generated file (Python 3 relative import issue)
RUN sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' orchestrator/generated/orchestrator_pb2_grpc.py

# Create a user to run the application (Security Best Practice)
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Environment Variables (Defaults, override at runtime)
ENV GRPC_PORT=50051
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 50051

# Command to run (as module)
CMD ["python", "-m", "orchestrator.main"]
