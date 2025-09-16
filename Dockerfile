# Multi-stage build for production
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -g 1001 appuser && \
    useradd -r -u 1001 -g appuser appuser

# Set working directory
WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY api/ ./api/
COPY health_check.py .
COPY .env.production .env

# Create data directory for SQLite database
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Make sure scripts in .local are usable
ENV PATH=/home/appuser/.local/bin:$PATH

# Expose port (Railway will set PORT env var)
EXPOSE 8000

# Health check (Railway will set PORT env var)
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD python health_check.py

# Run the application with uvicorn
CMD sh -c "echo '=== RAILWAY STARTUP DEBUG ===' && \
           echo 'PORT environment variable: $PORT' && \
           echo 'Current working directory:' && pwd && \
           echo 'Contents of /app:' && ls -la && \
           echo 'Contents of /app/api:' && ls -la api/ && \
           echo 'Python path:' && python -c 'import sys; print(sys.path)' && \
           echo 'Testing FastAPI import:' && python -c 'import fastapi; print(\"FastAPI imported successfully\")' && \
           echo 'Testing api.index import:' && python -c 'from api.index import app; print(\"App imported successfully\")' && \
           echo 'Starting uvicorn server...' && \
           uvicorn api.index:app --host 0.0.0.0 --port $PORT --log-level debug"