"""Base configuration classes for evaluation jobs."""

from dataclasses import dataclass, field
from enum import Enum


class TierName(Enum):
    """Evaluation tier names."""

    SMOKE = "smoke"  # Multiple times/day to daily, <1hr
    STANDARD = "standard"  # Multiple times/week to weekly, 1-2hr
    FULL = "full"  # Comprehensive suite, run sparingly


@dataclass
class StorageConfig:
    """Configuration for results storage (S3 + Postgres)."""

    s3_bucket: str
    s3_prefix: str
    s3_group: str

    def to_cli_args(self) -> list[str]:
        """Convert to olmo-eval CLI arguments."""
        return [
            "--store",
            "--s3-bucket", self.s3_bucket,
            "--s3-prefix", self.s3_prefix,
            "--s3-group", self.s3_group,
        ]


@dataclass
class ModelEval:
    """A single model evaluation configuration.

    Represents one `olmo-eval run` invocation = one Cloud Run Job instance.

    Overrides are positional on the CLI:
    - model_overrides: Applied after -m
    - task_overrides: Applied after each -t
    - harness_overrides: Applied after -H
    """

    model: str  # Model preset name (e.g., "cirrascale-olmo-3-7b-instruct")
    tasks: list[str]  # Task names or suite names
    harness: str = "default"
    model_overrides: dict[str, str] = field(default_factory=dict)
    task_overrides: dict[str, str] = field(default_factory=dict)
    harness_overrides: dict[str, str] = field(default_factory=dict)

    def to_cli_args(self, storage: StorageConfig | None = None) -> list[str]:
        """Convert to olmo-eval run CLI arguments.

        Generates args in order with positional overrides:
            -m {model} [-o {model_override}...]
            -t {task1} [-o {task_override}...]
            -t {task2} [-o {task_override}...]
            -H {harness} [-o {harness_override}...]
            [--store --s3-bucket ... ]
        """
        args: list[str] = []

        # Model with its overrides
        args.extend(["-m", self.model])
        for key, value in self.model_overrides.items():
            args.extend(["-o", f"{key}={value}"])

        # Tasks with their overrides (same overrides apply to each task)
        for task in self.tasks:
            args.extend(["-t", task])
            for key, value in self.task_overrides.items():
                args.extend(["-o", f"{key}={value}"])

        # Harness with its overrides
        args.extend(["-H", self.harness])
        for key, value in self.harness_overrides.items():
            args.extend(["-o", f"{key}={value}"])

        # Storage config
        if storage:
            args.extend(storage.to_cli_args())

        return args

    def job_name(self, tier_name: str) -> str:
        """Generate a Cloud Run Job name for this evaluation."""
        # e.g., "eval-smoke-cirrascale-olmo-3-7b-instruct"
        model_slug = self.model.replace("_", "-").lower()
        return f"eval-{tier_name}-{model_slug}"


@dataclass
class TierConfig:
    """Configuration for an evaluation tier.

    A tier defines a set of model evaluations that run on the same schedule.
    Each ModelEval becomes one parallel Cloud Run Job instance.
    """

    name: TierName
    schedule: str  # Cloud Scheduler cron expression (empty for manual trigger)
    timeout_minutes: int  # Max job duration
    storage: StorageConfig
    models: list[ModelEval]
    description: str = ""

    def get_jobs(self) -> list[tuple[ModelEval, list[str]]]:
        """Get all jobs for this tier as (ModelEval, cli_args) tuples."""
        return [(model, model.to_cli_args(self.storage)) for model in self.models]

    def get_job_by_index(self, index: int) -> tuple[ModelEval, list[str]]:
        """Get a specific job by task index (for CLOUD_RUN_TASK_INDEX)."""
        if index < 0 or index >= len(self.models):
            raise IndexError(f"Task index {index} out of range (0-{len(self.models) - 1})")
        model = self.models[index]
        return (model, model.to_cli_args(self.storage))

    @property
    def task_count(self) -> int:
        """Number of parallel tasks for this tier."""
        return len(self.models)

    def to_docker_run_cmd(self, model: ModelEval, image: str = "evaluations") -> str:
        """Generate a docker run command for a model evaluation."""
        env_vars = [
            "LITELLM_PROXY_API_KEY",
            "PGHOST",
            "PGPORT",
            "PGUSER",
            "PGPASSWORD",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
        ]
        env_flags = " \\\n  ".join(f"-e {var}=${var}" for var in env_vars)
        cli_args = " ".join(model.to_cli_args(self.storage))

        return f"docker run --rm \\\n  {env_flags} \\\n  {image} \\\n  {cli_args}"
