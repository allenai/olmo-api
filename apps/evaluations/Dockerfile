# Evaluations Docker Image for Cloud Run Jobs
#
# Build (requires GitHub token for private repo access):
#   docker build --platform linux/amd64 --build-arg GITHUB_TOKEN=$GITHUB_TOKEN \
#     -t evaluations -f apps/evaluations/Dockerfile apps/evaluations
#
# Once olmo-eval-internal is public, remove --build-arg GITHUB_TOKEN
#
# Run locally:
#   docker run -e LITELLM_PROXY_API_KEY=$LITELLM_PROXY_API_KEY evaluations \
#     -m cirrascale-olmo-3-7b-instruct -t humaneval:bpb -o limit=10 -H default
#
# Run tier (local mode):
#   docker run -e EVAL_TIER=standard -e CLOUD_RUN_TASK_INDEX=0 -e LOCAL=true \
#     -e LITELLM_PROXY_API_KEY=$LITELLM_PROXY_API_KEY evaluations

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

# Install git for cloning olmo-eval-internal
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# GitHub token for private repo access (pass with --build-arg GITHUB_TOKEN=xxx)
ARG GITHUB_TOKEN
RUN git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"

WORKDIR /app

# Copy evaluations package
COPY src /app/src
COPY pyproject.toml /app/pyproject.toml

# Install evaluations package (pulls olmo-eval-internal from git)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system /app

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM --platform=linux/amd64 python:3.12-slim-bookworm AS runner

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
