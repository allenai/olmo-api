#!/usr/bin/env python3
"""Run evaluations locally with Docker.

Usage:
    python run_local.py                      # Run standard tier, task 0, local mode
    python run_local.py --tier smoke         # Run smoke tier
    python run_local.py --task-index 1       # Run task index 1
    python run_local.py --with-storage       # Enable S3/Postgres storage
    python run_local.py --build              # Build image first
    python run_local.py --build-only         # Build image and exit

Environment variables are loaded from .env.local
"""

import os
import subprocess
import sys
from pathlib import Path

# Try to load .env.local
APP_DIR = Path(__file__).parent
ENV_FILE = APP_DIR / ".env.local"

if ENV_FILE.exists():
    print(f"Loading environment from {ENV_FILE}")
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    import argparse

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
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            print("Error: GITHUB_TOKEN is required for build", file=sys.stderr)
            return 1

        print("Building Docker image...")
        build_cmd = [
            "docker", "build",
            "--platform", "linux/amd64",
            "--build-arg", f"GITHUB_TOKEN={github_token}",
            "-t", args.image,
            "-f", str(APP_DIR / "Dockerfile"),
            str(APP_DIR),
        ]
        result = subprocess.run(build_cmd)
        if result.returncode != 0:
            return result.returncode

        if args.build_only:
            print(f"Build complete: {args.image}")
            return 0

    # Build docker run command
    docker_cmd = [
        "docker", "run", "--rm",
        "-e", f"EVAL_TIER={args.tier}",
        "-e", f"CLOUD_RUN_TASK_INDEX={args.task_index}",
        "-e", f"LITELLM_PROXY_API_KEY={os.environ.get('LITELLM_PROXY_API_KEY', '')}",
    ]

    if args.with_storage:
        docker_cmd.extend([
            "-e", f"PGHOST={os.environ.get('PGHOST', '')}",
            "-e", f"PGPORT={os.environ.get('PGPORT', '5432')}",
            "-e", f"PGUSER={os.environ.get('PGUSER', '')}",
            "-e", f"PGPASSWORD={os.environ.get('PGPASSWORD', '')}",
            "-e", f"AWS_ACCESS_KEY_ID={os.environ.get('AWS_ACCESS_KEY_ID', '')}",
            "-e", f"AWS_SECRET_ACCESS_KEY={os.environ.get('AWS_SECRET_ACCESS_KEY', '')}",
        ])
        print(f"Running: tier={args.tier}, task_index={args.task_index} (with storage)")
    else:
        docker_cmd.extend(["-e", "LOCAL=true"])
        print(f"Running: tier={args.tier}, task_index={args.task_index} (local mode, no storage)")

    docker_cmd.append(args.image)

    print()
    result = subprocess.run(docker_cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
