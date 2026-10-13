# ── Stage 1: Builder ──────────────────────────────────────────
# Install build tools and dependencies here.
# gcc and libpq-dev are NOT carried into the final image.
FROM python:3.13-slim AS builder

WORKDIR /app

# System packages needed to compile Python dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies before copying app code
# This allows Docker to cache this layer on rebuilds
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────
# Start fresh with a clean image — no compilers, smaller size.
FROM python:3.13-slim

WORKDIR /app

# Only the runtime library is needed here (not the dev headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment built in Stage 1
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Prevents .pyc files and enables real-time log output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]