# Evaluations Docker Image for Cloud Run Jobs
#
# Docker image with which to run a list of model evals basedb on tier configuration,
# and will run each individual model eval as it's own Google Cloud Job
#
# Build (requires GitHub token for private repo access):
#   docker build --platform linux/amd64 --secret id=GITHUB_TOKEN \
#     -t evaluations -f apps/evaluations/Dockerfile apps/evaluations
#
# Once olmo-eval-internal is public, remove --secret GITHUB_TOKEN
#
# Run tier (local mode, no storage):
#   docker run -e EVAL_TIER=standard -e CLOUD_RUN_TASK_INDEX=0 -e LOCAL=true \
#     -e LITELLM_PROXY_API_KEY=$LITELLM_PROXY_API_KEY evaluations
#
# Run builds/evals locally with helper script:
#   python run_local.py --tier standard --build
#   python run_local.py --build-only
#

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

# Install git for cloning olmo-eval-internal
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# GitHub token for private repo access (mounted as secret)
RUN --mount=type=secret,id=GITHUB_TOKEN \
    git config --global url."https://$(cat /run/secrets/GITHUB_TOKEN)@github.com/".insteadOf "https://github.com/"

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
FROM --platform=linux/amd64 python:3.14-slim-bookworm AS runner

# Install runtime dependencies
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Setup non-root user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin/olmo-eval /usr/local/bin/olmo-eval
COPY --from=builder /usr/local/bin/evaluations /usr/local/bin/evaluations

WORKDIR /app

# Use non-root user
USER nonroot

ENV PYTHONUNBUFFERED=1
ENV TERM=dumb
ENV NO_COLOR=1

# Use Python CLI as entrypoint
ENTRYPOINT ["python", "-m", "evaluations.cli"]
