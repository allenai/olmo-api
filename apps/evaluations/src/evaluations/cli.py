"""CLI for evaluations Cloud Run Jobs."""

import argparse
import os
import subprocess
import sys

from evaluations.configs import ModelEval, TierName, get_tier
from evaluations.logging import logger


def run_ad_hoc(
    model: str,
    tasks: str,
    provider_kind: str = "litellm",
    harness_overrides: str | None = None,
    *,
    local: bool,
) -> int:
    """Run an ad-hoc model evaluation.

    Args:
        model: Provider model path (e.g., "litellm_proxy/openai/Olmo-7B").
        tasks: Comma-separated task names.
        provider_kind: Provider type (default: "litellm").
        harness_overrides: Semicolon-separated key:value pairs.
        local: Skip storage flags if True.

    Returns:
        Exit code from olmo-eval.
    """
    model_eval = ModelEval.from_ad_hoc(
        model=model,
        tasks=tasks,
        provider_kind=provider_kind,
        harness_overrides=harness_overrides,
    )

    cli_args = model_eval.to_cli_args(storage=None)

    logger.info("Ad-hoc evaluation")
    logger.info("Model: %s", model)
    logger.info("Tasks: %s", tasks)
    logger.info("Provider: %s", provider_kind)
    if harness_overrides:
        logger.info("Harness overrides: %s", harness_overrides)
    logger.info("Local mode: %s", local)

    cmd = ["olmo-eval", "run", *cli_args]
    logger.info("Running: %s", " ".join(cmd))

    result = subprocess.run(cmd, check=False)
    return result.returncode


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

    Modes (checked in order):
    1. EVAL_MODE=ad-hoc: Run ad-hoc evaluation from env vars
    2. EVAL_TIER set: Run tier evaluation
    3. CLI arguments: Manual invocation
    """
    local_mode = os.environ.get("LOCAL", "").lower() == "true"

    # Check for ad-hoc mode
    eval_mode = os.environ.get("EVAL_MODE", "")
    if eval_mode == "ad-hoc":
        ad_hoc_model = os.environ.get("AD_HOC_MODEL")
        ad_hoc_tasks = os.environ.get("AD_HOC_TASKS")

        if not ad_hoc_model or not ad_hoc_tasks:
            logger.error("Ad-hoc mode requires AD_HOC_MODEL and AD_HOC_TASKS env vars")
            sys.exit(1)

        provider_kind = os.environ.get("AD_HOC_PROVIDER_KIND", "litellm")
        harness_overrides = os.environ.get("AD_HOC_HARNESS_OVERRIDES")

        sys.exit(
            run_ad_hoc(
                model=ad_hoc_model,
                tasks=ad_hoc_tasks,
                provider_kind=provider_kind,
                harness_overrides=harness_overrides,
                local=local_mode,
            )
        )

    # Check for EVAL_TIER env var (Cloud Run Jobs tier mode)
    eval_tier = os.environ.get("EVAL_TIER")
    if eval_tier:
        task_index = int(os.environ.get("CLOUD_RUN_TASK_INDEX", "0"))
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

    # ad-hoc subcommand
    adhoc_parser = subparsers.add_parser(
        "ad-hoc",
        help="Run an ad-hoc model evaluation",
    )
    adhoc_parser.add_argument(
        "--model",
        required=True,
        help="Provider model path (e.g., litellm_proxy/openai/Olmo-7B)",
    )
    adhoc_parser.add_argument(
        "--tasks",
        required=True,
        help="Comma-separated task names (e.g., humaneval:bpb,mbpp:bpb)",
    )
    adhoc_parser.add_argument(
        "--provider-kind",
        default="litellm",
        help="Provider type (default: litellm)",
    )
    adhoc_parser.add_argument(
        "--harness-overrides",
        help="Semicolon-separated key:value pairs (e.g., metrics.enabled:true;limit:10)",
    )
    adhoc_parser.add_argument(
        "--local",
        action="store_true",
        help="Skip storage (no --store, S3, or Postgres)",
    )

    args = parser.parse_args()

    if args.command == "run-tier":
        sys.exit(run_tier(args.tier_name, args.task_index, local=args.local))
    elif args.command == "ad-hoc":
        sys.exit(
            run_ad_hoc(
                model=args.model,
                tasks=args.tasks,
                provider_kind=args.provider_kind,
                harness_overrides=args.harness_overrides,
                local=args.local,
            )
        )


if __name__ == "__main__":
    main()
