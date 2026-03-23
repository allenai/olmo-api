"""Evaluation job configurations.

This module contains Python-defined job configurations
for running evaluations via Cloud Run Jobs.

Structure:
- base.py: Core dataclasses (TierConfig, ModelEval, StorageConfig)
- tiers/: Tier definitions with model evaluations
  - smoke.py: Quick sanity checks (multiple times/day to daily)
  - standard.py: Curated standard evals (multiple times/week to weekly)
  - full.py: Comprehensive evals (run sparingly)

Usage:
    from evaluations.configs import smoke_tier, standard_tier, full_tier
    from evaluations.configs import TierName, get_tier, list_tiers

    # Get all jobs for smoke tier
    for model, cli_args in smoke_tier.get_jobs():
        print(model.model, cli_args)

    # Generate docker run command
    cmd = smoke_tier.to_docker_run_cmd(smoke_tier.models[0])
"""

from evaluations.configs.base import (
    ModelEval,
    StorageConfig,
    TierConfig,
    TierName,
)
from evaluations.configs.tiers import (
    ALL_TIERS,
    full_tier,
    get_tier,
    list_tiers,
    smoke_tier,
    standard_tier,
)

__all__ = [  # noqa: RUF022
    # Base classes
    "ModelEval",
    "StorageConfig",
    "TierConfig",
    "TierName",
    # Tier instances
    "smoke_tier",
    "standard_tier",
    "full_tier",
    # Registry
    "ALL_TIERS",
    "get_tier",
    "list_tiers",
]
