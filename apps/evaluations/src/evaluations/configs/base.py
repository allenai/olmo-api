"""Base configuration classes for evaluation jobs."""

from dataclasses import dataclass, field


@dataclass
class EvalJobConfig:
    """Configuration for an evaluation job.

    Attributes:
        name: Human-readable name for this job configuration.
        model: Model preset name (e.g., "cirrascale-olmo-3-7b-instruct").
        task: Task specification with optional variant (e.g., "humaneval:bpb").
        harness: Harness preset name (e.g., "default").
        limit: Maximum number of examples to evaluate.
        overrides: Additional overrides as key-value pairs.
        required_env_vars: Environment variables required to run this job.
    """

    name: str
    model: str
    task: str
    harness: str = "default"
    limit: int | None = None
    overrides: dict[str, str] = field(default_factory=dict)
    required_env_vars: list[str] = field(default_factory=list)

    def to_cli_args(self) -> list[str]:
        """Convert this config to CLI arguments for olmo-eval run."""
        args = [
            "-m", self.model,
            "-t", self.task,
            "-H", self.harness,
        ]

        if self.limit is not None:
            args.extend(["-o", f"limit={self.limit}"])

        for key, value in self.overrides.items():
            args.extend(["-o", f"{key}={value}"])

        return args

    def to_docker_run_cmd(self, image: str = "evaluations") -> str:
        """Generate a docker run command for this job."""
        env_flags = " ".join(f"-e {var}=${var}" for var in self.required_env_vars)
        cli_args = " ".join(self.to_cli_args())

        return f"docker run --rm {env_flags} {image} {cli_args}".strip()
