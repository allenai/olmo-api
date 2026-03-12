"""CLI for evaluations Cloud Run Jobs."""

import argparse
import os
import subprocess
import sys

from evaluations.configs import TierName, get_tier
from evaluations.logging import logger


def run_tier(tier_name: str, task_index: int, *, local: bool) -> int:
    """Run a specific model evaluation from a tier.

    Args:
        tier_name: Tier to run (smoke, standard, full).
        task_index: CLOUD_RUN_TASK_INDEX for parallelism.
        local: Skip storage flags if True.

    Returns:
        Exit code from olmo-eval.
    """
    tier = get_tier(TierName(tier_name))

    try:
        model, cli_args = tier.get_job_by_index(task_index)
    except IndexError as e:
        logger.error("Error: %s", e)
        return 1

    # For local testing, remove storage flags
    if local:
        cli_args = model.to_cli_args(storage=None, tier_harness_overrides=tier.harness_overrides)

    logger.info("Tier: %s", tier_name)
    logger.info("Task index: %d/%d", task_index, tier.task_count - 1)
    logger.info("Model: %s", model.model)
    logger.info("Tasks: %s", ", ".join(model.tasks))
    logger.info("Local mode: %s", local)

    # Build the olmo-eval command
    cmd = ["olmo-eval", "run", *cli_args]
    logger.info("Running: %s", " ".join(cmd))

    # Execute olmo-eval run
    result = subprocess.run(cmd, check=False)
    return result.returncode


def main() -> None:
    """Evaluations CLI entry point.

    If EVAL_TIER env var is set, automatically runs that tier.
    Otherwise, use 'run-tier' subcommand.
    """
    # Check for EVAL_TIER env var (Cloud Run Jobs mode)
    eval_tier = os.environ.get("EVAL_TIER")
    if eval_tier:
        task_index = int(os.environ.get("CLOUD_RUN_TASK_INDEX", "0"))
        local_mode = os.environ.get("LOCAL", "").lower() == "true"
        sys.exit(run_tier(eval_tier, task_index, local=local_mode))

    # CLI mode
    parser = argparse.ArgumentParser(
        description="Evaluations CLI for Cloud Run Jobs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run-tier subcommand
    run_parser = subparsers.add_parser(
        "run-tier",
        help="Run a specific model evaluation from a tier",
    )
    run_parser.add_argument(
        "tier_name",
        choices=[t.value for t in TierName],
        help="Tier to run (smoke, standard, full)",
    )
    run_parser.add_argument(
        "--task-index",
        type=int,
        required=True,
        help="CLOUD_RUN_TASK_INDEX for parallelism",
    )
    run_parser.add_argument(
        "--local",
        action="store_true",
        help="Skip storage (no --store, S3, or Postgres)",
    )

    args = parser.parse_args()

    if args.command == "run-tier":
        sys.exit(run_tier(args.tier_name, args.task_index, local=args.local))


if __name__ == "__main__":
    main()
