# syntax=docker/dockerfile:1

# Build dependencies in a virtual environment
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install .

# Runtime image
FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PORT=8000

# Install security updates and runtime dependencies
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy virtual environment and application code
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY pyproject.toml README.md ./
COPY gunicorn.conf.py ./

# Create non-root user with proper permissions
RUN groupadd -r -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup appuser && \
    mkdir -p uploads logs reports /tmp/prometheus && \
    chown -R appuser:appgroup /app /tmp/prometheus && \
    chmod -R 755 /app && \
    chmod -R 777 uploads logs reports /tmp/prometheus

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Enhanced health check with readiness probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/readiness || exit 1

# Use Gunicorn for production with optimized settings
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app.main:app"]

# Development image with tooling and hot reload
FROM production AS development

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir ".[dev]"

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
