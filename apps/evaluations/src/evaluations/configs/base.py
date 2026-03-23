"""Base configuration classes for evaluation jobs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from evaluations.logging import logger
from evaluations.settings import settings

# Pattern for valid harness override keys (dotted config paths like "metrics.enabled", "limit")
_VALID_KEY_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$")


def parse_harness_overrides(harness_overrides: str) -> dict[str, str]:
    """Parse and validate harness overrides string.

    Args:
        harness_overrides: Semicolon-separated key:value pairs (e.g., "metrics.enabled:true;limit:10").
            Semicolons are used as delimiters to avoid conflicts with gcloud --update-env-vars
            which uses commas to separate environment variables.

    Returns:
        Dictionary of parsed overrides.

    Raises:
        ValueError: If format is invalid (missing colon, empty key/value).
    """
    parsed: dict[str, str] = {}

    for override_item in harness_overrides.split(";"):
        item = override_item.strip()
        if not item:
            continue

        if ":" not in item:
            msg = (
                f"Invalid harness override '{item}': missing ':' delimiter. "
                f"Expected format 'key:value' (e.g., 'metrics.enabled:true;limit:10')"
            )
            raise ValueError(msg)

        key, value = item.split(":", 1)
        key, value = key.strip(), value.strip()

        if not key:
            msg = f"Invalid harness override '{item}': empty key. Expected format 'key:value'"
            raise ValueError(msg)

        if not value:
            msg = f"Invalid harness override '{item}': empty value for key '{key}'. Expected format 'key:value'"
            raise ValueError(msg)

        # Warn if key doesn't look like a valid config path
        if not _VALID_KEY_PATTERN.match(key):
            logger.warning(
                "Harness override key '%s' doesn't match expected pattern "
                "(alphanumeric with dots, e.g., 'metrics.enabled'). "
                "This may cause errors in olmo-eval.",
                key,
            )

        parsed[key] = value

    return parsed


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
            "--s3-bucket",
            self.s3_bucket,
            "--s3-prefix",
            self.s3_prefix,
            "--s3-group",
            self.s3_group,
        ]


@dataclass
class ModelEval:
    """A single model evaluation configuration.

    Represents one `olmo-eval run` invocation = one Cloud Run Job instance.

    Provider overrides configure the model via harness provider settings:
    - provider_overrides: Applied as -o provider.{key}={value} after -H
    - task_overrides: Applied after each -t
    - harness_overrides: Applied after -H (for non-provider settings)

    The olmo-eval CLI requires provider config via harness overrides, not model overrides.
    """

    model: str  # Provider preset, or Display name when provider_overrides are used.
    tasks: list[str]  # Task names or suite names
    harness: str = "default"  # Harness preset
    provider_overrides: dict[str, str] = field(default_factory=dict)
    task_overrides: dict[str, str] = field(default_factory=dict)
    harness_overrides: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_ad_hoc(
        cls,
        model: str,
        tasks: str,
        provider_kind: str = "litellm",
        harness_overrides: str | None = None,
    ) -> ModelEval:
        """Create a ModelEval from ad-hoc environment variables.

        Args:
            model: Provider model path (e.g., "litellm_proxy/openai/Olmo-7B").
            tasks: Comma-separated task names (e.g., "humaneval:bpb,mbpp:bpb").
            provider_kind: Provider type (default: "litellm").
            harness_overrides: Semicolon-separated key:value pairs (e.g., "metrics.enabled:true;limit:10").

        Returns:
            A ModelEval configured for ad-hoc execution.
        """
        task_list = [t.strip() for t in tasks.split(",") if t.strip()]

        provider_overrides = {
            "kind": provider_kind,
            "model": model,
            "api_base": settings.LITELLM_API_BASE,
        }

        parsed_harness_overrides: dict[str, str] = {}
        if harness_overrides:
            parsed_harness_overrides = parse_harness_overrides(harness_overrides)

        # Use model path as display name (last part)
        display_name = model.split("/")[-1] if "/" in model else model

        return cls(
            model=display_name,
            tasks=task_list,
            provider_overrides=provider_overrides,
            harness_overrides=parsed_harness_overrides,
        )

    def to_cli_args(
        self,
        storage: StorageConfig | None = None,
        tier_harness_overrides: dict[str, str] | None = None,
    ) -> list[str]:
        """Convert to olmo-eval run CLI arguments.

        Generates args in order:
            -m {model}
            -t {task1} [-o {task_override}...]
            -t {task2} [-o {task_override}...]
            -H {harness} [-o provider.{key}={value}...] [-o {harness_override}...]
            [--store --s3-bucket ... ]

        Provider overrides are applied to the harness config, which takes precedence
        over the -m model preset lookup.

        Args:
            storage: Storage config (None for local mode).
            tier_harness_overrides: Harness overrides from TierConfig (applied before model overrides).
        """
        args: list[str] = []

        # Model name (used for preset lookup, but provider_overrides take precedence)
        args.extend(["-m", self.model])

        # Tasks with their overrides (same overrides apply to each task)
        for task in self.tasks:
            args.extend(["-t", task])
            for key, value in self.task_overrides.items():
                args.extend(["-o", f"{key}={value}"])

        # Harness with provider overrides and other harness overrides
        args.extend(["-H", self.harness])
        for key, value in self.provider_overrides.items():
            args.extend(["-o", f"provider.{key}={value}"])

        # Metrics reporters based on storage mode (can be overridden by tier/model harness_overrides)
        if storage:
            args.extend(["-o", "metrics.reporters=[console,db]"])
        else:
            args.extend(["-o", "metrics.reporters=[console,file]"])

        # Tier-level harness overrides
        if tier_harness_overrides:
            for key, value in tier_harness_overrides.items():
                args.extend(["-o", f"{key}={value}"])

        # Model-level harness overrides (can override tier-level)
        for key, value in self.harness_overrides.items():
            args.extend(["-o", f"{key}={value}"])

        # Storage config
        if storage:
            args.extend(storage.to_cli_args())

        return args


@dataclass
class TierConfig:
    """Configuration for an evaluation tier.

    A tier defines a set of model evaluations that run together.
    Each ModelEval becomes one parallel Cloud Run Job task.
    """

    name: TierName
    timeout_minutes: int  # Max job duration
    storage: StorageConfig
    models: list[ModelEval]
    description: str = ""
    harness_overrides: dict[str, str] = field(default_factory=dict)
    schedule: str | None = None  # Cron expression for Cloud Scheduler, None = manual only

    def get_jobs(self) -> list[tuple[ModelEval, list[str]]]:
        """Get all jobs for this tier as (ModelEval, cli_args) tuples."""
        return [(model, model.to_cli_args(self.storage, self.harness_overrides)) for model in self.models]

    def get_job_by_index(self, index: int) -> tuple[ModelEval, list[str]]:
        """Get a specific job by task index (for CLOUD_RUN_TASK_INDEX)."""
        if index < 0 or index >= len(self.models):
            msg = f"Task index {index} out of range (0-{len(self.models) - 1})"
            raise IndexError(msg)

        model = self.models[index]
        return (model, model.to_cli_args(self.storage, self.harness_overrides))

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
        cli_args = " ".join(model.to_cli_args(self.storage, self.harness_overrides))

        return f"docker run --rm \\\n  {env_flags} \\\n  {image} \\\n  {cli_args}"
