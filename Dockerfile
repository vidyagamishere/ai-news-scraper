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

# Copy application code and requirements (Railway needs this in runtime)
COPY api/ /app/api/
COPY health_check.py .
COPY requirements.txt .
COPY .env.production .env
# Copy existing SQLite database if it exists
COPY ai_news.db ./ai_news.db

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
           echo 'File version check - first 20 lines of api/index.py:' && head -n 20 /app/api/index.py && \
           echo 'Searching for FastAPI app creation:' && grep -n 'app = FastAPI' /app/api/index.py || echo 'FastAPI app creation not found!' && \
           echo 'File size:' && wc -l /app/api/index.py && \
           echo 'Testing api.index module import:' && python -c 'import api.index; print(\"Module imported successfully\")' && \
           echo 'Checking module attributes:' && python -c 'import api.index; print(\"Module attributes:\", [attr for attr in dir(api.index) if not attr.startswith(\"_\")])' && \
           echo 'Looking for app in module:' && python -c 'import api.index; print(\"Has app attribute:\", hasattr(api.index, \"app\"))' && \
           uvicorn api.index:app --host 0.0.0.0 --port $PORT --log-level debug"