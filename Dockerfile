# ==============================================================================
# Faraday: 100% Air-Gapped Code Assurance Copilot
# Production Linux Container Image
# Multi-arch support: linux/amd64, linux/arm64 (Snapdragon Linux / aarch64)
# ==============================================================================

FROM python:3.11-slim-bookworm

LABEL maintainer="Monishwaran K"
LABEL description="Faraday 100% Air-gapped on-device AI code review & assurance copilot"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install minimal OS dependencies for git & AST parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency configuration first for layer caching
COPY pyproject.toml README.md ./

# Install project dependencies
RUN pip install --upgrade pip && \
    pip install .

# Copy application source and models
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY models/ ./models/

# Default workspace directory for mounted projects
WORKDIR /workspace

# Default entrypoint to faraday CLI
ENTRYPOINT ["faraday"]
CMD ["--help"]
