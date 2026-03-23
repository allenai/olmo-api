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

Scheduling is configured in each tier's Python config via the `schedule` field (cron expression).

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

# LiteLLM proxy configuration
LITELLM_API_BASE = "https://ai2-model-hub.allen.ai"

standard_tier = TierConfig(
    name=TierName.STANDARD,
    description="Curated standard evaluations",
    timeout_minutes=120,
    storage=STANDARD_STORAGE,
    schedule="0 2 * * 1,4",  # Monday and Thursday at 2am UTC
    models=[
        ModelEval(
            model="olmo-3-7b-instruct-cirrascale",  # Display name
            provider_overrides={
                "kind": "litellm",
                "model": "litellm_proxy/openai/Olmo-3-7B-Instruct",
                "api_base": LITELLM_API_BASE,
            },
            tasks=["humaneval:bpb", "mbpp:bpb"],
            task_overrides={"limit": "10"},
            harness_overrides={"metrics.enabled": "true"},
        ),
        # Add more models here...
    ],
)
```

### ModelEval Options

- `model`: Display name for the model (used in logs and results, also passed to -m for preset fallback)
- `provider_overrides`: Dict of provider config overrides (applied via `-o provider.{key}={value}`):
  - `kind`: Provider type (`litellm`, `vllm`, `vllm_server`, `hf`)
  - `model`: Model path (e.g., `litellm_proxy/openai/Olmo-3-7B-Instruct`)
  - `api_base`: API base URL for the provider
  - `max_concurrency`: Max concurrent requests
  - `dtype`: Data type (`auto`, `float16`, `bfloat16`)
- `tasks`: List of task names or suites (e.g., `humaneval:bpb`, `mbpp:pass_at_10`)
- `harness`: Harness name (default: `"default"`)
- `task_overrides`: Dict of task-level overrides (applied to all tasks)
- `harness_overrides`: Dict of harness-level overrides (non-provider settings)

### Cloud Run Job Configuration

Infrastructure is managed with Terraform, with configuration derived from Python tier configs:

```
terraform/
├── main.tf              # Provider and backend config
├── variables.tf         # Input variables
├── outputs.tf           # Exported values
├── cloud_run_jobs.tf    # Cloud Run Job resources
├── schedulers.tf        # Cloud Scheduler resources
├── generate_tfvars.py   # Generates tfvars from Python configs
└── .gitignore           # Ignores state and generated files
```

Job settings (timeout, task count, schedule) come from `TierConfig` in Python. Resource allocation (CPU, memory) is defined in `cloud_run_jobs.tf`.

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

Use `run-local` to build and run evaluations:

```bash
# Build the Docker image
uv run run-local --build-only

# Run standard tier, task index 0 (local mode, no storage)
uv run run-local

# Run a specific tier (default is smoke)
uv run run-local --tier smoke

# Run a specific task index (for multi-model tiers)
uv run run-local --task-index 1

# Run with storage enabled (S3 + Postgres)
uv run run-local --with-storage

# Build and run in one command
uv run run-local --build --tier standard
```

### Running Tests

```bash
# Run all tests (no private repo access needed)
uv run --only-group dev pytest
```

### Docker Commands

You can also run Docker directly:

```bash
# Build
docker build --platform linux/amd64 \
  --secret id=GITHUB_TOKEN,env=GITHUB_TOKEN \
  -t evaluations -f Dockerfile .

# Run tier (local mode)
docker run --rm \
  -e EVAL_TIER=standard \
  -e CLOUD_RUN_TASK_INDEX=0 \
  -e LOCAL=true \
  -e LITELLM_PROXY_API_KEY=$LITELLM_PROXY_API_KEY \
  evaluations
```

## Deployment

### CI/CD

The GitHub Actions workflow (`.github/workflows/build-and-push-evals.yml`) automatically builds and deploys on push to `main` when files in `apps/evaluations/` change. It uses Terraform to manage Cloud Run Jobs and Cloud Schedulers.

### Manual Deployment

```bash
# Ensure you're logged in and project is set
gcloud auth login
gcloud config set project ai2-skiff2-playground

# Generate tfvars from Python tier configs
uv run generate-tfvars -o terraform/terraform.tfvars.json

# Navigate to terraform directory
cd terraform

# Initialize Terraform (first time only)
terraform init

# Preview changes
terraform plan -var="project_id=ai2-skiff2-playground"

# Apply changes
terraform apply -var="project_id=ai2-skiff2-playground"
```

### Terraform State

Terraform state is stored in a GCS bucket (`ai2-skiff2-playground-tf-state`). This enables:
- Team collaboration (shared state)
- Drift detection
- Rollback via version control

### Manual Push to Artifact Registry

```bash
# Configure Docker for Artifact Registry
gcloud auth configure-docker us-west1-docker.pkg.dev

# Tag and push
docker tag evaluations us-west1-docker.pkg.dev/ai2-skiff2-playground/model-evals/evaluations:latest
docker push us-west1-docker.pkg.dev/ai2-skiff2-playground/model-evals/evaluations:latest
```

## Executing Jobs

A single Cloud Run Job (`eval`) handles all evaluation modes. Task count and environment variables are passed at execution time.

### Execute a Tier

```bash
# Run smoke tier (2 parallel tasks)
gcloud run jobs execute eval --region us-west1 \
  --tasks 2 \
  --update-env-vars "EVAL_TIER=smoke"

# Run standard tier
gcloud run jobs execute eval --region us-west1 \
  --tasks 2 \
  --update-env-vars "EVAL_TIER=standard"
```

### Execute Ad-Hoc Evaluation

Run a single model/task combination without adding it to tier configs:

```bash
gcloud run jobs execute eval --region us-west1 \
  --tasks 1 \
  --update-env-vars "EVAL_MODE=ad-hoc,AD_HOC_MODEL=litellm_proxy/openai/Olmo-7B,AD_HOC_TASKS=humaneval:bpb"

# With harness overrides
gcloud run jobs execute eval --region us-west1 \
  --tasks 1 \
  --update-env-vars "EVAL_MODE=ad-hoc,AD_HOC_MODEL=litellm_proxy/openai/Olmo-7B,AD_HOC_TASKS=humaneval:bpb,AD_HOC_HARNESS_OVERRIDES=metrics.enabled:true"
```

### Ad-Hoc Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `EVAL_MODE` | Set to `ad-hoc` | Yes |
| `AD_HOC_MODEL` | Provider model path (e.g., `litellm_proxy/openai/Olmo-7B`) | Yes |
| `AD_HOC_TASKS` | Comma-separated task names (e.g., `humaneval:bpb,mbpp:bpb`) | Yes |
| `AD_HOC_PROVIDER_KIND` | Provider type (default: `litellm`) | No |
| `AD_HOC_HARNESS_OVERRIDES` | Semicolon-separated key:value pairs (e.g., `metrics.enabled:true;limit:10`) | No |

## CLI Reference

The `evaluations` CLI is available inside the container:

```bash
# Auto-run tier from env vars (used by Cloud Run)
EVAL_TIER=standard CLOUD_RUN_TASK_INDEX=0 evaluations

# Auto-run ad-hoc from env vars
EVAL_MODE=ad-hoc AD_HOC_MODEL=litellm_proxy/openai/Olmo-7B AD_HOC_TASKS=humaneval:bpb evaluations

# Show help
evaluations --help

# Run a specific tier/task
evaluations run-tier standard --task-index 0
evaluations run-tier smoke --task-index 0 --local

# Run ad-hoc evaluation
evaluations ad-hoc --model litellm_proxy/openai/Olmo-7B --tasks humaneval:bpb --local
```
