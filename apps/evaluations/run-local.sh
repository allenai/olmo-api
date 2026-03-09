#!/bin/bash
# Run evaluations locally with Docker
#
# Usage:
#   ./run-local.sh                           # Run standard tier, task 0, local mode
#   ./run-local.sh --tier smoke              # Run smoke tier
#   ./run-local.sh --task-index 1            # Run task index 1
#   ./run-local.sh --with-storage            # Enable S3/Postgres storage
#   ./run-local.sh --build                   # Build image first
#
# Environment variables are loaded from .env.local

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env.local if it exists
if [ -f "$SCRIPT_DIR/.env.local" ]; then
  echo "Loading environment from .env.local"
  set -a
  source "$SCRIPT_DIR/.env.local"
  set +a
fi

# Defaults
TIER="standard"
TASK_INDEX=0
LOCAL_MODE=true
DO_BUILD=false
IMAGE="evaluations"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --tier)
      TIER="$2"
      shift 2
      ;;
    --task-index)
      TASK_INDEX="$2"
      shift 2
      ;;
    --with-storage)
      LOCAL_MODE=false
      shift
      ;;
    --build)
      DO_BUILD=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: ./run-local.sh [--tier TIER] [--task-index N] [--with-storage] [--build]"
      exit 1
      ;;
  esac
done

# Build if requested
if [ "$DO_BUILD" = true ]; then
  echo "Building Docker image..."
  if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN is required for build"
    exit 1
  fi
  docker build --platform linux/amd64 \
    --build-arg "GITHUB_TOKEN=$GITHUB_TOKEN" \
    -t "$IMAGE" \
    -f "$SCRIPT_DIR/Dockerfile" \
    "$SCRIPT_DIR"
fi

# Build docker run command
DOCKER_ARGS=(
  "docker" "run" "--rm"
  "-e" "EVAL_TIER=$TIER"
  "-e" "CLOUD_RUN_TASK_INDEX=$TASK_INDEX"
  "-e" "LITELLM_PROXY_API_KEY=$LITELLM_PROXY_API_KEY"
)

if [ "$LOCAL_MODE" = true ]; then
  DOCKER_ARGS+=("-e" "LOCAL=true")
  echo "Running: tier=$TIER, task_index=$TASK_INDEX (local mode, no storage)"
else
  DOCKER_ARGS+=(
    "-e" "PGHOST=$PGHOST"
    "-e" "PGPORT=${PGPORT:-5432}"
    "-e" "PGUSER=$PGUSER"
    "-e" "PGPASSWORD=$PGPASSWORD"
    "-e" "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID"
    "-e" "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY"
  )
  echo "Running: tier=$TIER, task_index=$TASK_INDEX (with storage)"
fi

DOCKER_ARGS+=("$IMAGE")

echo ""
"${DOCKER_ARGS[@]}"
