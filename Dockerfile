# Use a slim Python image
FROM python:3.10-slim-bullseye

# Install system dependencies for screenshot tools (if needed in Docker)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv
COPY --from=astral-sh/setup-uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:${PATH}"

# Copy configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies (without the app itself)
RUN uv sync --no-dev --no-install-project

# Copy the app
COPY obsidian_clipper obsidian_clipper/
COPY README.md .

# Install the project
RUN uv sync --no-dev

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:${PATH}"

# Default command
ENTRYPOINT ["obsidian-clipper"]
