"""Generate Cloud Run Job YAML files from tier configurations.

Usage:
    uv run python generate_jobs.py                    # Generate all tier YAMLs
    uv run python generate_jobs.py --project my-proj  # With specific project ID
    uv run python generate_jobs.py --image IMAGE      # With specific image tag
"""

import argparse
import sys
from pathlib import Path

from evaluations.configs import list_tiers

JOB_TEMPLATE = """\
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: eval-{tier_name}
  labels:
    tier: {tier_name}
  annotations:
    run.googleapis.com/launch-stage: BETA
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/execution-environment: gen2
    spec:
      parallelism: {task_count}
      taskCount: {task_count}
      template:
        spec:
          containers:
            - image: {image}
              resources:
                limits:
                  cpu: "4"
                  memory: 8Gi
              env:
                - name: EVAL_TIER
                  value: {tier_name}
                - name: LOCAL
                  value: "true"
                - name: LITELLM_PROXY_API_KEY
                  valueFrom:
                    secretKeyRef:
                      name: litellm-proxy-api-key
                      key: latest
          timeoutSeconds: {timeout_seconds}
"""


def generate_yaml(tier_name: str, task_count: int, timeout_minutes: int, project: str, image: str | None) -> str:
    """Generate YAML for a single tier."""
    if image is None:
        image = f"us-west1-docker.pkg.dev/{project}/model-evals/evaluations:latest"

    return JOB_TEMPLATE.format(
        tier_name=tier_name,
        task_count=task_count,
        timeout_seconds=timeout_minutes * 60,
        image=image,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Cloud Run Job YAMLs from tier configs")
    parser.add_argument("--project", default="my-project", help="GCP project ID (default: my-project, replaced by deploy.sh)")
    parser.add_argument("--image", help="Full image tag (default: uses project to construct)")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent, help="Output directory for YAMLs")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for tier in list_tiers():
        tier_name = tier.name.value
        yaml_content = generate_yaml(
            tier_name=tier_name,
            task_count=tier.task_count,
            timeout_minutes=tier.timeout_minutes,
            project=args.project,
            image=args.image,
        )

        output_path = args.output_dir / f"{tier_name}.yaml"
        output_path.write_text(yaml_content)
        print(f"Generated {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
