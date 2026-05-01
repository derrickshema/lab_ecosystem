# ============================================================
# BACKEND DOCKERFILE
# ============================================================
# This file tells Docker how to build an image for the FastAPI backend.
# Think of an "image" as a snapshot/template, and a "container" as a 
# running instance of that image.
#
# We use a "multi-stage build" to keep the final image small:
# 1. First stage: Install dependencies
# 2. Second stage: Copy only what we need to run
# ============================================================

# ------------------------------------------------------------
# STAGE 1: Builder
# ------------------------------------------------------------
# Start from the official Python image
# "slim" means it's a minimal version without extra packages
# This keeps the image smaller (faster downloads, less disk space)
FROM python:3.13-slim AS builder

# Set the working directory inside the container
# All following commands run from this directory
WORKDIR /app

# Install system dependencies needed to build Python packages
# - gcc: C compiler (some Python packages need to compile C code)
# - libpq-dev: PostgreSQL client library (needed for psycopg2)
# We install these in the builder stage only (not in final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
# This isolates our Python packages from the system Python
RUN python -m venv /opt/venv

# Add the virtual environment to PATH
# Now 'pip' and 'python' use the venv automatically
ENV PATH="/opt/venv/bin:$PATH"

# Copy only requirements.txt first (not the whole app)
# Docker caches each layer, so if requirements.txt doesn't change,
# Docker reuses the cached layer (faster rebuilds!)
COPY requirements.txt .

# Install Python dependencies into the virtual environment
# --no-cache-dir: Don't store pip's cache (smaller image)
RUN pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------
# STAGE 2: Runtime (Final Image)
# ------------------------------------------------------------
# Start fresh from a clean Python image
# This means we don't include gcc and other build tools
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install only runtime dependencies (not build tools)
# libpq5: PostgreSQL client library (runtime version)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
# This is the magic of multi-stage builds!
COPY --from=builder /opt/venv /opt/venv

# Add venv to PATH
ENV PATH="/opt/venv/bin:$PATH"

# Set Python environment variables
# PYTHONDONTWRITEBYTECODE: Don't create .pyc files (smaller image)
# PYTHONUNBUFFERED: Print output immediately (better for logs)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy the application code
# The .dockerignore file controls what gets copied
COPY . .

# Expose port 8000 (documentation for humans, doesn't actually open the port)
# The actual port mapping happens in docker-compose.yml
EXPOSE 8000

# Health check - Docker will periodically run this command
# If it fails, Docker marks the container as "unhealthy"
# --interval: Check every 30 seconds
# --timeout: Give up after 10 seconds
# --retries: Mark unhealthy after 3 failures
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# The command to run when the container starts
# uvicorn: ASGI server for FastAPI
# --host 0.0.0.0: Listen on all network interfaces (required in Docker)
# --port 8000: Port to listen on
# Note: We don't use --reload in production (it's for development)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


