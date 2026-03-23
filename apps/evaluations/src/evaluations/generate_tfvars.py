"""Generate terraform.tfvars.json from Python tier configurations.

This script reads the tier configurations from the evaluations package
and outputs a JSON file that Terraform can consume as variable values.

Usage:
    uv run generate-tfvars                                    # Output to stdout
    uv run generate-tfvars -o terraform/terraform.tfvars.json # Output to file

This ensures the Python tier configs remain the single source of truth
for both runtime (CLI) and infrastructure (Terraform) configuration.
"""

import argparse
import json
import sys
from pathlib import Path

from evaluations.configs import list_tiers
from evaluations.logging import logger


def generate_tfvars() -> dict:
    """Generate Terraform variables from tier configurations."""
    tiers = {}
    max_timeout = 0
    max_tasks = 0

    for tier in list_tiers():
        tier_name = tier.name.value
        tiers[tier_name] = {
            "task_count": tier.task_count,
            "timeout_minutes": tier.timeout_minutes,
            "schedule": tier.schedule,
        }
        max_timeout = max(max_timeout, tier.timeout_minutes)
        max_tasks = max(max_tasks, tier.task_count)

    return {
        "tiers": tiers,
        "max_task_timeout_minutes": max_timeout,
        "max_parallel_task_count": max_tasks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate terraform.tfvars.json from Python tier configs")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file (default: stdout)",
    )
    args = parser.parse_args()

    tfvars = generate_tfvars()
    json_output = json.dumps(tfvars, indent=2)

    if args.output:
        args.output.write_text(json_output + "\n")
        logger.info("Generated %s", args.output)
    else:
        print(json_output)  # noqa: T201 - stdout is the intended output

    return 0


if __name__ == "__main__":
    sys.exit(main())
