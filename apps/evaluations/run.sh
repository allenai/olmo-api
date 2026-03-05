#!/bin/bash
# Entrypoint script for olmo-eval Cloud Run Jobs
#
# Passes all arguments to olmo-eval run command.
# Secrets should be passed as environment variables:
#   - OPENAI_API_KEY
#   - ANTHROPIC_API_KEY
#   - etc.

set -e

echo "Starting olmo-eval run..."
echo "Arguments: $@"

exec olmo-eval run "$@"
