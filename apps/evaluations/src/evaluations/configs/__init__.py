"""Evaluation job configurations.

This module contains Python-defined job configurations
for running evaluations via Cloud Run Jobs.
"""

from evaluations.configs.base import EvalJobConfig
from evaluations.configs.olmo3 import olmo3_7b_humaneval_bpb

__all__ = [
    "EvalJobConfig",
    "olmo3_7b_humaneval_bpb",
]
