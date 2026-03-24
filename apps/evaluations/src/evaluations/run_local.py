"""Run evaluations locally with Docker.

Usage:
    uv run run-local                      # Run standard tier, task 0, local mode
    uv run run-local --tier smoke         # Run smoke tier
    uv run run-local --task-index 1       # Run task index 1
    uv run run-local --with-storage       # Enable S3/Postgres storage
    uv run run-local --build              # Build image first
    uv run run-local --build-only         # Build image and exit

Environment variables are loaded from .env.local
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from evaluations.logging import logger
from evaluations.settings import settings

# App directory is two levels up from this file (src/evaluations/ -> apps/evaluations/)
APP_DIR = Path(__file__).parent.parent.parent


def main() -> int:
    """Run evaluations locally with Docker."""

    parser = argparse.ArgumentParser(description="Run evaluations locally with Docker")
    parser.add_argument("--tier", default="standard", help="Tier to run (default: standard)")
    parser.add_argument("--task-index", type=int, default=0, help="Task index (default: 0)")
    parser.add_argument("--with-storage", action="store_true", help="Enable S3/Postgres storage")
    parser.add_argument("--build", action="store_true", help="Build image first")
    parser.add_argument("--build-only", action="store_true", help="Build image and exit")
    parser.add_argument("--image", default="evaluations", help="Image name (default: evaluations)")
    args = parser.parse_args()

    # Build if requested
    if args.build or args.build_only:
        if not settings.GITHUB_TOKEN:
            logger.error("GITHUB_TOKEN is required for build")
            return 1

        # Set env var for Docker secret mounting
        os.environ["GITHUB_TOKEN"] = settings.GITHUB_TOKEN

        logger.info("Building Docker image...")
        build_cmd = [
            "docker",
            "build",
            "--platform",
            "linux/amd64",
            "--secret",
            "id=GITHUB_TOKEN,env=GITHUB_TOKEN",
            "-t",
            args.image,
            "-f",
            str(APP_DIR / "Dockerfile"),
            str(APP_DIR),
        ]
        result = subprocess.run(build_cmd, check=False)
        if result.returncode != 0:
            return result.returncode

        if args.build_only:
            logger.info("Build complete: %s", args.image)
            return 0

    # Build docker run command
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-e",
        f"EVAL_TIER={args.tier}",
        "-e",
        f"CLOUD_RUN_TASK_INDEX={args.task_index}",
        "-e",
        f"LITELLM_PROXY_API_KEY={settings.LITELLM_PROXY_API_KEY or ''}",
    ]

    if args.with_storage:
        docker_cmd.extend([
            "-e",
            f"PGHOST={settings.PGHOST}",
            "-e",
            f"PGPORT={settings.PGPORT}",
            "-e",
            f"PGUSER={settings.PGUSER}",
            "-e",
            f"AWS_ACCESS_KEY_ID={settings.AWS_ACCESS_KEY_ID or ''}",
            "-e",
            f"AWS_SECRET_ACCESS_KEY={settings.AWS_SECRET_ACCESS_KEY or ''}",
        ])
        # Use DB_SECRET_ARN if set, otherwise pass PGPASSWORD directly
        if settings.DB_SECRET_ARN:
            docker_cmd.extend(["-e", f"DB_SECRET_ARN={settings.DB_SECRET_ARN}"])
            logger.info("Running: tier=%s, task_index=%d (with storage, AWS secrets)", args.tier, args.task_index)
        elif settings.PGPASSWORD:
            docker_cmd.extend(["-e", f"PGPASSWORD={settings.PGPASSWORD}"])
            logger.info("Running: tier=%s, task_index=%d (with storage)", args.tier, args.task_index)
        else:
            logger.warning("Neither DB_SECRET_ARN nor PGPASSWORD is set")
            logger.info("Running: tier=%s, task_index=%d (with storage, no password)", args.tier, args.task_index)
    else:
        docker_cmd.extend(["-e", "LOCAL=true"])
        logger.info("Running: tier=%s, task_index=%d (local mode, no storage)", args.tier, args.task_index)

    docker_cmd.append(args.image)

    result = subprocess.run(docker_cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
