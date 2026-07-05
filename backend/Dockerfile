# Stage 1: Runtime environment using Python 3.11 slim
FROM python:3.11-slim

# Setup non-interactive shell and environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/warehouse/hr_analytics.duckdb \
    HOST=0.0.0.0 \
    PORT=8000 \
    DEBUG=false

WORKDIR /app

# Install system dependencies (curl for health check)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create a secure, rootless user/group and set directory permissions
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser && \
    mkdir -p /app/warehouse && \
    chown -R appuser:appgroup /app

# Switch to rootless user
USER appuser

# Expose backend service port
EXPOSE 8000

# Health check configuration
HEALTHCHECK --interval=10s --timeout=5s --retries=3 --start-period=5s \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
