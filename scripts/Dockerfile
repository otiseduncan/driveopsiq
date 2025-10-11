# SyferStackV2 Audit System
# Production-ready audit container with all dependencies

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r audit && useradd -r -g audit audit

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional audit tools
RUN pip install --no-cache-dir \
    ruff \
    bandit \
    mypy \
    safety \
    pylint \
    black \
    isort \
    flake8 \
    pytest \
    pytest-cov \
    pytest-asyncio

# Copy application code
COPY scripts/ /app/scripts/
COPY audit_config.yaml /app/scripts/

# Create directories for reports and cache
RUN mkdir -p /app/reports /app/.audit_cache && \
    chown -R audit:audit /app

# Switch to non-root user
USER audit

# Set Python path
ENV PYTHONPATH=/app/scripts

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "/app/scripts/production_audit.py"]