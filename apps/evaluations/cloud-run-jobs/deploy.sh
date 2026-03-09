#!/bin/bash
# Deploy Cloud Run Jobs
#
# Usage:
#   ./deploy.sh                    # Deploy jobs only (no schedulers)
#   ./deploy.sh --with-schedulers  # Deploy jobs and create schedulers
#
# Environment variables:
#   GCP_PROJECT  - GCP project ID (required)
#   GCP_REGION   - GCP region (default: us-central1)
#   IMAGE_TAG    - Full image tag to use (optional, updates YAML if provided)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
PROJECT="${GCP_PROJECT:?Error: GCP_PROJECT environment variable is required}"
REGION="${GCP_REGION:-us-west1}"
SERVICE_ACCOUNT="evaluations@${PROJECT}.iam.gserviceaccount.com"
WITH_SCHEDULERS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --with-schedulers)
      WITH_SCHEDULERS=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Deploying to project: $PROJECT"
echo "Region: $REGION"

# Create temp directory for processed YAMLs
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Deploy Cloud Run Jobs
for tier in smoke standard full; do
  YAML_FILE="$SCRIPT_DIR/${tier}.yaml"
  if [ -f "$YAML_FILE" ]; then
    echo "Deploying eval-${tier}..."

    # Copy and process YAML
    PROCESSED_YAML="$TEMP_DIR/${tier}.yaml"
    cp "$YAML_FILE" "$PROCESSED_YAML"

    # Replace placeholders
    sed -i.bak "s|my-project|${PROJECT}|g" "$PROCESSED_YAML"

    # If IMAGE_TAG is provided, update the image
    if [ -n "$IMAGE_TAG" ]; then
      sed -i.bak "s|gcr.io/${PROJECT}/evaluations:latest|${IMAGE_TAG}|g" "$PROCESSED_YAML"
    fi

    gcloud run jobs replace "$PROCESSED_YAML" --region "$REGION" --project "$PROJECT"
  fi
done

# Create Cloud Scheduler jobs (optional)
if [ "$WITH_SCHEDULERS" = true ]; then
  echo ""
  echo "Creating Cloud Schedulers..."

  echo "Creating scheduler eval-smoke-schedule..."
  gcloud scheduler jobs delete eval-smoke-schedule --location "$REGION" --project "$PROJECT" --quiet 2>/dev/null || true
  gcloud scheduler jobs create http eval-smoke-schedule \
    --location "$REGION" \
    --project "$PROJECT" \
    --schedule "0 */6 * * *" \
    --time-zone "UTC" \
    --uri "https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT/jobs/eval-smoke:run" \
    --http-method POST \
    --oauth-service-account-email "$SERVICE_ACCOUNT"

  echo "Creating scheduler eval-standard-schedule..."
  gcloud scheduler jobs delete eval-standard-schedule --location "$REGION" --project "$PROJECT" --quiet 2>/dev/null || true
  gcloud scheduler jobs create http eval-standard-schedule \
    --location "$REGION" \
    --project "$PROJECT" \
    --schedule "0 2 * * 1,4" \
    --time-zone "UTC" \
    --uri "https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT/jobs/eval-standard:run" \
    --http-method POST \
    --oauth-service-account-email "$SERVICE_ACCOUNT"

  # eval-full: No schedule (manual trigger only)
fi

echo ""
echo "Done!"
echo ""
echo "Manual execution commands:"
echo "  gcloud run jobs execute eval-smoke --region $REGION --project $PROJECT"
echo "  gcloud run jobs execute eval-standard --region $REGION --project $PROJECT"
echo "  gcloud run jobs execute eval-full --region $REGION --project $PROJECT"



 docker run --rm \
    -e EVAL_TIER=standard \
    -e CLOUD_RUN_TASK_INDEX=0 \
    -e LITELLM_PROXY_API_KEY=$LITELLM_PROXY_API_KEY \
    -e PGHOST=$PGHOST \
    -e PGPASSWORD=$PGPASSWORD \
    evaluations