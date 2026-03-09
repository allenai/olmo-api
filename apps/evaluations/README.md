# Evaluations

Cloud Run Jobs application for running OLMo model evaluations at scale.

This application wraps [olmo-eval-internal](https://github.com/allenai/olmo-eval-internal) to provide scheduled, tiered evaluation runs across multiple models and evaluation tasks.

## Overview

Evaluations are organized into **tiers** with different scopes:

| Tier | Description | Timeout |
|------|-------------|---------|
| `smoke` | Quick sanity checks | 1 hour |
| `standard` | Curated standard evals | 2 hours |
| `full` | Comprehensive suite | 6 hours |

Each tier defines a list of models to evaluate. When a tier runs as a Cloud Run Job, each model runs as a parallel task using `CLOUD_RUN_TASK_INDEX`.

Scheduling is configured separately in `cloud-run-jobs/deploy.sh` using Cloud Scheduler.

## Configuration

### Tier Configuration Files

Tier configurations are defined in Python:

```
src/evaluations/configs/
├── base.py           # Core dataclasses (TierConfig, ModelEval, StorageConfig)
└── tiers/
    ├── smoke.py      # Smoke tier configuration
    ├── standard.py   # Standard tier configuration
    └── full.py       # Full tier configuration
```

### Adding or Modifying Models

Edit the appropriate tier file in `src/evaluations/configs/tiers/`. Each tier has a `models` list:

```python
from evaluations.configs.base import ModelEval, StorageConfig, TierConfig, TierName

standard_tier = TierConfig(
    name=TierName.STANDARD,
    description="Curated standard evaluations",
    timeout_minutes=120,
    storage=STANDARD_STORAGE,
    models=[
        ModelEval(
            model="cirrascale-olmo-3-7b-instruct",  # Model preset name
            tasks=["humaneval:bpb", "mbpp:bpb"],    # Evaluation tasks
            task_overrides={"limit": "10"},         # Per-task overrides
            harness_overrides={"metrics.enabled": "true"},  # Harness overrides
        ),
        # Add more models here...
    ],
)
```

### ModelEval Options

- `model`: Model preset name (defined in olmo-eval-internal)
- `tasks`: List of task names or suites (e.g., `humaneval:bpb`, `mbpp:pass_at_10`)
- `harness`: Harness name (default: `"default"`)
- `model_overrides`: Dict of model-level overrides
- `task_overrides`: Dict of task-level overrides (applied to all tasks)
- `harness_overrides`: Dict of harness-level overrides

### Cloud Run Job YAML Files

The Cloud Run Job definitions are in `cloud-run-jobs/`:

```
cloud-run-jobs/
├── smoke.yaml      # Smoke tier job definition
├── standard.yaml   # Standard tier job definition
├── full.yaml       # Full tier job definition
├── deploy.sh       # Deployment script
└── teardown.sh     # Teardown script
```

To change resource allocation (CPU, memory) or timeout, edit the YAML files directly.

## Local Development

### Prerequisites

1. Docker installed and running
2. GitHub token with access to `allenai/olmo-eval-internal` (until repo is public)
3. LiteLLM proxy API key for model inference (use labs-evals virtual key)

### Setup

1. Copy the example environment file:
   ```bash
   cp .env.local.example .env.local
   ```

2. Fill in the required values in `.env.local`:
   ```bash
   # Required for Docker build (private repo access)
   GITHUB_TOKEN=ghp_xxxx

   # Required for running evaluations
   LITELLM_PROXY_API_KEY=sk-xxxx

   # Required for storage (if using --with-storage)
   PGHOST=your-db-host
   PGPASSWORD=xxxx
   AWS_ACCESS_KEY_ID=xxxx
   AWS_SECRET_ACCESS_KEY=xxxx

   # Optional for storage (defaults shown)
   PGPORT=5432
   PGUSER=postgres
   ```

### Running Locally

Use `run_local.py` to build and run evaluations:

```bash
# Build the Docker image
python run_local.py --build-only

# Run standard tier, task index 0 (local mode, no storage)
python run_local.py

# Run a specific tier
python run_local.py --tier smoke

# Run a specific task index (for multi-model tiers)
python run_local.py --task-index 1

# Run with storage enabled (S3 + Postgres)
python run_local.py --with-storage

# Build and run in one command
python run_local.py --build --tier standard
```

### Docker Commands

You can also run Docker directly:

```bash
# Build
docker build --platform linux/amd64 \
  --build-arg GITHUB_TOKEN=$GITHUB_TOKEN \
  -t evaluations -f Dockerfile .

# Run tier (local mode)
docker run --rm \
  -e EVAL_TIER=standard \
  -e CLOUD_RUN_TASK_INDEX=0 \
  -e LOCAL=true \
  -e LITELLM_PROXY_API_KEY=$LITELLM_PROXY_API_KEY \
  evaluations

# List available commands
docker run --rm evaluations --help

# List tiers
docker run --rm evaluations list-tiers

# List jobs in a tier
docker run --rm evaluations list-jobs standard
```

## Deployment

### CI/CD

The GitHub Actions workflow (`.github/workflows/build-and-push-evals.yml`) automatically builds and deploys on push to `main` when files in `apps/evaluations/` change.

### Manual Deployment

```bash
# Ensure you're logged in and project is set
gcloud auth login
gcloud config set project ai2-skiff2-playground

# Deploy Cloud Run Jobs
cd cloud-run-jobs
./deploy.sh

# Deploy with schedulers
./deploy.sh --with-schedulers
```

### Manual Push to Artifact Registry

```bash
# Configure Docker for Artifact Registry
gcloud auth configure-docker us-west1-docker.pkg.dev

# Tag and push
docker tag evaluations us-west1-docker.pkg.dev/ai2-skiff2-playground/model-evals/evaluations:latest
docker push us-west1-docker.pkg.dev/ai2-skiff2-playground/model-evals/evaluations:latest
```

## CLI Reference

The `evaluations` CLI is available inside the container:

```bash
# Auto-run tier from env vars (used by Cloud Run)
EVAL_TIER=standard CLOUD_RUN_TASK_INDEX=0 evaluations

# Run a specific tier/task
evaluations run-tier standard --task-index 0
evaluations run-tier smoke --task-index 0 --local

# List available tiers
evaluations list-tiers

# List jobs in a tier
evaluations list-jobs standard
```
