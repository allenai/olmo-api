#!/bin/bash
# Deploy Cloud Run Jobs
#
# Usage:
#   ./deploy.sh                    # Deploy jobs only (no schedulers)
#   ./deploy.sh --with-schedulers  # Deploy jobs and create schedulers
#
# Prerequisites:
#   - Logged into gcloud CLI: gcloud auth login
#   - Project set: gcloud config set project <project-id>
#
# Optional environment variables:
#   IMAGE_TAG    - Full image tag to use (default: latest from Artifact Registry)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env.local if it exists
if [ -f "$APP_DIR/.env.local" ]; then
  set -a
  source "$APP_DIR/.env.local"
  set +a
fi

# Configuration
REGION="us-west1"

# Get project from gcloud config
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT" ] || [ "$PROJECT" = "(unset)" ]; then
  echo "Error: No GCP project set. Run: gcloud config set project <project-id>"
  exit 1
fi

# Get default compute service account from gcloud
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format="value(projectNumber)" 2>/dev/null)
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

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

# Create temp directory for generated YAMLs
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Generate YAMLs from Python tier configs
echo "Generating job YAMLs..."
GENERATE_ARGS="--project $PROJECT --output-dir $TEMP_DIR"
if [ -n "$IMAGE_TAG" ]; then
  GENERATE_ARGS="$GENERATE_ARGS --image $IMAGE_TAG"
fi

# Run generator (use uv if available, otherwise python)
if command -v uv &> /dev/null; then
  (cd "$APP_DIR" && uv run python "$SCRIPT_DIR/generate_jobs.py" $GENERATE_ARGS)
else
  python "$SCRIPT_DIR/generate_jobs.py" $GENERATE_ARGS
fi

# Deploy Cloud Run Jobs
for tier in smoke standard full; do
  YAML_FILE="$TEMP_DIR/${tier}.yaml"
  if [ -f "$YAML_FILE" ]; then
    echo ""
    echo "Deploying eval-${tier}..."
    gcloud run jobs replace "$YAML_FILE" --region "$REGION" --project "$PROJECT"
  fi
done

# Create Cloud Scheduler jobs (optional)
if [ "$WITH_SCHEDULERS" = true ]; then
  echo ""
  echo "Creating Cloud Schedulers..."
  echo "Using service account: $SERVICE_ACCOUNT"

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
