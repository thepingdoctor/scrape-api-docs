# Multi-stage Dockerfile for Documentation Scraper
# Optimized for production deployment with minimal image size

# ========================================
# Stage 1: Build dependencies
# ========================================
FROM python:3.11-slim as builder

# Build arguments
ARG PYTHON_VERSION=3.11

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION}

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (without dev dependencies)
RUN poetry install --no-root --no-dev --no-interaction --no-ansi

# Copy application code
COPY src/ ./src/
COPY README.md ./

# Install the project
RUN poetry install --no-dev --no-interaction --no-ansi

# ========================================
# Stage 2: Runtime image
# ========================================
FROM python:3.11-slim as runtime

# Metadata labels
LABEL org.opencontainers.image.title="Documentation Scraper"
LABEL org.opencontainers.image.description="API documentation scraper with CLI, API, and web interface"
LABEL org.opencontainers.image.authors="Adam Blackington"
LABEL org.opencontainers.image.url="https://github.com/thepingdoctor/scrape-api-docs"
LABEL org.opencontainers.image.source="https://github.com/thepingdoctor/scrape-api-docs"
LABEL org.opencontainers.image.vendor="Documentation Scraper Project"
LABEL org.opencontainers.image.licenses="MIT"

# Create non-root user for security
RUN groupadd -r scraper && useradd -r -g scraper scraper

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    SCRAPER_OUTPUT_DIR=/data \
    SCRAPER_CACHE_DIR=/cache

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create data directories
RUN mkdir -p /data /cache /app && \
    chown -R scraper:scraper /data /cache /app

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=scraper:scraper /app/.venv /app/.venv
COPY --from=builder --chown=scraper:scraper /app/src /app/src
COPY --from=builder --chown=scraper:scraper /app/README.md /app/

# Switch to non-root user
USER scraper

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import scrape_api_docs; print('healthy')" || exit 1

# Expose ports
# 8501 - Streamlit UI
# 8000 - API server (if implemented)
EXPOSE 8501 8000

# Volume for output data
VOLUME ["/data", "/cache"]

# Default command: Run CLI
ENTRYPOINT ["python", "-m", "scrape_api_docs"]
CMD ["--help"]

# ========================================
# Stage 3: Development image (optional)
# ========================================
FROM runtime as development

USER root

# Install development dependencies
COPY --from=builder /app/pyproject.toml /app/poetry.lock ./
RUN pip install poetry==${POETRY_VERSION:-1.7.1} && \
    poetry install --no-interaction --no-ansi

# Install additional dev tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

USER scraper

# Development command
CMD ["/bin/bash"]
