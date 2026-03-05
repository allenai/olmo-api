"""Smoke tier configuration.

Quick sanity checks that run multiple times per day to daily.
Should complete in under 1 hour with simple pass/fail results.
"""

from evaluations.configs.base import ModelEval, StorageConfig, TierConfig, TierName

SMOKE_STORAGE = StorageConfig(
    s3_bucket="olmo-eval-results",
    s3_prefix="smoke",
    s3_group="daily",
)

smoke_tier = TierConfig(
    name=TierName.SMOKE,
    description="Quick sanity checks, simple pass/fail, <1 hour",
    schedule="0 */6 * * *",  # Every 6 hours
    timeout_minutes=60,
    storage=SMOKE_STORAGE,
    models=[
        # Cirrascale deployments
        ModelEval(
            model="cirrascale-olmo-3-7b-instruct",
            tasks=[
                "smoke_identity_olmo",
                "smoke_hello",
                "smoke_tools",
            ],
        ),
        # Modal deployments
        ModelEval(
            model="modal-olmo-3-7b-instruct",
            tasks=[
                "smoke_identity_olmo",
                "smoke_hello",
                "smoke_tools",
            ],
        ),
        # Add more models as they are deployed...
    ],
)
