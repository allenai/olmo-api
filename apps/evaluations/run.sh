#!/bin/bash
# Entrypoint script for olmo-eval Cloud Run Jobs
#
# Supports two modes:
#
# 1. Direct CLI args (pass arguments directly):
#    docker run evaluations -m model -t task ...
#
# 2. Tier + task index (for Cloud Run Jobs parallelism):
#    EVAL_TIER=smoke CLOUD_RUN_TASK_INDEX=0 docker run evaluations
#
# Required environment variables for storage:
#   - LITELLM_PROXY_API_KEY
#   - PGHOST, PGPORT, PGUSER, PGPASSWORD
#   - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

set -e

# If EVAL_TIER is set, use tier-based execution with task index
if [ -n "$EVAL_TIER" ]; then
    TASK_INDEX=${CLOUD_RUN_TASK_INDEX:-0}
    echo "Running tier: $EVAL_TIER, task index: $TASK_INDEX"

    # Add --local flag if LOCAL=true (skips storage)
    LOCAL_FLAG=""
    if [ "$LOCAL" = "true" ]; then
        LOCAL_FLAG="--local"
        echo "Local mode: storage disabled"
    fi

    exec python -m evaluations.cli run-tier "$EVAL_TIER" --task-index "$TASK_INDEX" $LOCAL_FLAG
fi

# Otherwise, pass all arguments directly to olmo-eval run
echo "Starting olmo-eval run..."
echo "Arguments: $@"

exec olmo-eval run "$@"
