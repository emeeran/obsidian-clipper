# Stage 1: Build dependencies
FROM python:3.12-slim-bookworm AS builder

# Install uv
COPY --from=astral-sh/setup-uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:${PATH}"

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

COPY obsidian_clipper obsidian_clipper/
RUN uv sync --no-dev

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY obsidian_clipper obsidian_clipper/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:${PATH}"

# Run as non-root user
USER appuser

# Default command
ENTRYPOINT ["obsidian-clipper"]
