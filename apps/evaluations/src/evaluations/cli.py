"""CLI for evaluations Cloud Run Jobs."""

import subprocess
import sys

import click

from evaluations.configs import TierName, get_tier


@click.group()
def main() -> None:
    """Evaluations CLI for Cloud Run Jobs."""
    pass


@main.command()
@click.argument("tier_name", type=click.Choice([t.value for t in TierName]))
@click.option("--task-index", type=int, required=True, help="CLOUD_RUN_TASK_INDEX")
@click.option("--local", is_flag=True, help="Skip storage (no --store, S3, or Postgres)")
def run_tier(tier_name: str, task_index: int, local: bool) -> None:
    """Run a specific model evaluation from a tier.

    TIER_NAME is the tier to run (smoke, standard, deployment).
    --task-index corresponds to CLOUD_RUN_TASK_INDEX for parallelism.
    """
    tier = get_tier(TierName(tier_name))

    try:
        model, cli_args = tier.get_job_by_index(task_index)
    except IndexError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # For local testing, remove storage flags
    if local:
        cli_args = model.to_cli_args(storage=None)

    click.echo(f"Tier: {tier_name}")
    click.echo(f"Task index: {task_index}/{tier.task_count - 1}")
    click.echo(f"Model: {model.model}")
    click.echo(f"Tasks: {', '.join(model.tasks)}")
    click.echo(f"Local mode: {local}")
    click.echo()

    # Build the olmo-eval command
    cmd = ["olmo-eval", "run", *cli_args]
    click.echo(f"Running: {' '.join(cmd)}")
    click.echo()

    # Execute olmo-eval run
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


@main.command()
@click.argument("tier_name", type=click.Choice([t.value for t in TierName]))
def list_jobs(tier_name: str) -> None:
    """List all jobs in a tier."""
    tier = get_tier(TierName(tier_name))

    click.echo(f"Tier: {tier_name}")
    click.echo(f"Schedule: {tier.schedule or '(manual)'}")
    click.echo(f"Task count: {tier.task_count}")
    click.echo()

    for i, (model, cli_args) in enumerate(tier.get_jobs()):
        click.echo(f"[{i}] {model.model}")
        click.echo(f"    Tasks: {', '.join(model.tasks)}")
        click.echo(f"    Job name: {model.job_name(tier_name)}")
        click.echo()


@main.command()
def list_tiers() -> None:
    """List all available tiers."""
    from evaluations.configs import list_tiers as _list_tiers

    for tier in _list_tiers():
        click.echo(f"{tier.name.value}:")
        click.echo(f"  Description: {tier.description}")
        click.echo(f"  Schedule: {tier.schedule or '(manual)'}")
        click.echo(f"  Task count: {tier.task_count}")
        click.echo(f"  Timeout: {tier.timeout_minutes} min")
        click.echo()


if __name__ == "__main__":
    main()
