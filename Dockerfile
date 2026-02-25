# Obsidian Clipper - Ultra-slim Production Docker Image
# Multi-stage build with minimal final image size

# =============================================================================
# Stage 1: Build dependencies and wheel
# =============================================================================
FROM python:3.11-alpine AS builder

WORKDIR /build

# Install build dependencies (minimal set)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev

# Copy only what's needed for dependency resolution
COPY pyproject.toml ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies only (not the package itself yet)
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir requests python-dotenv

# =============================================================================
# Stage 2: Build the application wheel
# =============================================================================
FROM python:3.11-alpine AS wheel-builder

WORKDIR /build

COPY pyproject.toml README.md ./
COPY obsidian_clipper/ ./obsidian_clipper/

# Build wheel
RUN pip install --no-cache-dir --upgrade build && \
    python -m build --wheel

# =============================================================================
# Stage 3: Production image (minimal)
# =============================================================================
FROM python:3.11-alpine AS production

WORKDIR /app

# Install only essential runtime dependencies
# tesseract-ocr is optional - only needed for OCR functionality
RUN apk add --no-cache \
    libstdc++ \
    tesseract-ocr \
    tesseract-ocr-data-eng \
    && rm -rf /var/cache/apk/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=wheel-builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Create non-root user for security
RUN adduser -D -s /bin/sh appuser
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONDONTWARNPIPVERSIONCHECK=1 \
    LOG_FORMAT=json \
    PYTHONFAULTHANDLER=1

# Default configuration
ENV OBSIDIAN_HOST="127.0.0.1" \
    OBSIDIAN_PORT="27124" \
    LOG_LEVEL="WARNING"

# Health check (lightweight)
HEALTHCHECK --interval=60s --timeout=5s --start-period=2s --retries=2 \
    CMD python -c "import obsidian_clipper" || exit 1

# Entry point
ENTRYPOINT ["obsidian-clipper"]
CMD ["--help"]

# =============================================================================
# Alternative: Distroless image (even smaller, no shell)
# Uncomment to use - note: no tesseract, no health check possible
# =============================================================================
# FROM gcr.io/distroless/python3-debian12:latest AS distroless
#
# COPY --from=builder /opt/venv /opt/venv
# COPY obsidian_clipper/ /app/obsidian_clipper/
#
# ENV PATH="/opt/venv/bin:$PATH" \
#     PYTHONUNBUFFERED=1
#
# WORKDIR /app
# ENTRYPOINT ["obsidian-clipper"]
