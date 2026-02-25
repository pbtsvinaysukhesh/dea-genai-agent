# Use official Python runtime as base image
FROM python:3.11-slim

# Set metadata
LABEL maintainer="Your Name <your.email@example.com>"
LABEL description="On-Device AI Memory Intelligence Agent - Docker Container"
LABEL version="0.1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copy project files with exclusions handled by .dockerignore
COPY . .

# Create necessary directories
RUN mkdir -p data/knowledge \
    data/email_sent_tracker \
    data/hitl_review \
    logs \
    results/daily \
    models

# Set permissions
RUN chmod +x main.py || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command - can be overridden
CMD ["python", "main.py"]

# Expose ports if running web dashboard
EXPOSE 8000 11434

# Security: Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
