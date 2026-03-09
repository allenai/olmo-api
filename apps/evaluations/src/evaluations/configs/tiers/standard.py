"""Standard tier configuration.

Curated standard evaluations that run multiple days per week to weekly.
Should complete in 1-2 hours.
"""

from evaluations.configs.base import ModelEval, StorageConfig, TierConfig, TierName

STANDARD_STORAGE = StorageConfig(
    s3_bucket="olmo-eval-results",
    s3_prefix="standard",
    s3_group="weekly",
)

standard_tier = TierConfig(
    name=TierName.STANDARD,
    description="Curated standard evaluations, 1-2 hours",
    timeout_minutes=120,
    storage=STANDARD_STORAGE,
    models=[
        ModelEval(
            model="cirrascale-olmo-3-7b-instruct",
            tasks=[
                "humaneval:bpb",
            ],
            task_overrides={"limit": "10"},
            harness_overrides={"metrics.enabled": "true"},
        ),
        ModelEval(
            model="modal-olmo-3-7b-instruct",
            tasks=[
                "humaneval:bpb",
            ],
            task_overrides={"limit": "10"},
            harness_overrides={"metrics.enabled": "true"},
        ),
        # Add more models as they are deployed...
    ],
)
