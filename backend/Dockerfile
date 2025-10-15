# Backend Dockerfile for Smart Support Operator API
# Multi-stage build for optimized production image

FROM python:3.12-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy root requirements (classification module dependencies)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend requirements
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy source code
COPY src/ /app/src/
COPY backend/src/ /app/backend/src/

# Copy data assets (FAQ database, embeddings)
COPY docs/ /app/docs/
COPY data/ /app/data/

# Create data directory if it doesn't exist
RUN mkdir -p /app/data

# Set Python path to include both root and backend
ENV PYTHONPATH=/app:/app/backend:$PYTHONPATH

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Run uvicorn server
CMD ["python", "-m", "uvicorn", "backend.src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
