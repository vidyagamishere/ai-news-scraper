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
# Copy the new modular FastAPI architecture
COPY app/ /app/app/
COPY api/ /app/api/
COPY db_service.py .
COPY main.py .
COPY comprehensive_ai_sources.py .
COPY health_check.py .
COPY requirements.txt .
COPY .env.production .env
# Copy existing SQLite database for migration to PostgreSQL
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

# Run the application with modular FastAPI architecture
CMD sh -c "echo '=== RAILWAY MODULAR STARTUP DEBUG ===' && \
           echo 'PORT environment variable: $PORT' && \
           echo 'Project structure verification:' && \
           echo 'Main files:' && ls -la /app/*.py && \
           echo 'App directory:' && ls -la /app/app/ && \
           echo 'App routers:' && ls -la /app/app/routers/ && \
           echo 'Testing main module import:' && python -c 'import main; print(\"Main module imported successfully\")' && \
           echo 'Testing app.main module import:' && python -c 'from app.main import app; print(\"Modular app imported successfully\")' && \
           echo 'Database service check:' && python -c 'import db_service; print(\"Database service imported successfully\")' && \
           python main.py"