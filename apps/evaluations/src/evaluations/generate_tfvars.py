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


def generate_tfvars() -> dict:
    """Generate Terraform variables from tier configurations."""
    tiers = {}

    for tier in list_tiers():
        tier_name = tier.name.value
        tiers[tier_name] = {
            "task_count": tier.task_count,
            "timeout_minutes": tier.timeout_minutes,
            "schedule": tier.schedule,
        }

    return {"tiers": tiers}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate terraform.tfvars.json from Python tier configs"
    )
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
        print(f"Generated {args.output}", file=sys.stderr)
    else:
        print(json_output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
