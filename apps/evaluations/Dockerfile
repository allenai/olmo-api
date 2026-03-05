# Evaluations Docker Image for Cloud Run Jobs
#
# Build:
#   1. Copy olmo-eval-internal into the build context:
#      cp -r ~/dev/olmo-eval-internal apps/evaluations/olmo-eval-internal
#
#   2. Build the image:
#      docker build -t evaluations -f apps/evaluations/Dockerfile apps/evaluations
#
# Run:
#   docker run -e OPENAI_API_KEY=xxx evaluations \
#     -m openai/gpt-4o -o provider.kind=litellm \
#     -t mmlu -o limit=10

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy olmo-eval-internal source
COPY olmo-eval-internal /app/olmo-eval-internal

# Copy evaluations package
COPY src /app/src
COPY pyproject.toml /app/pyproject.toml

# Install olmo-eval-internal with litellm and storage extras, plus evaluations package
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system /app/olmo-eval-internal[litellm,storage] && \
    uv pip install --system /app

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM python:3.12-slim-bookworm AS runner

# Install runtime dependencies
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Setup non-root user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/olmo-eval /usr/local/bin/olmo-eval
COPY --from=builder /usr/local/bin/evaluations /usr/local/bin/evaluations

# Copy entrypoint script
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

WORKDIR /app

# Use non-root user
USER nonroot

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/run.sh"]
