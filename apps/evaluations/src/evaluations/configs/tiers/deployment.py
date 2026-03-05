"""Deployment tier configuration.

Comprehensive evaluations that run once at deployment time.
Triggered manually, not scheduled.
"""

from evaluations.configs.base import ModelEval, StorageConfig, TierConfig, TierName

DEPLOYMENT_STORAGE = StorageConfig(
    s3_bucket="olmo-eval-results",
    s3_prefix="deployment",
    s3_group="release",
)

deployment_tier = TierConfig(
    name=TierName.DEPLOYMENT,
    description="Comprehensive evaluation at deployment, run manually",
    schedule="",  # Not scheduled, triggered manually
    timeout_minutes=360,
    storage=DEPLOYMENT_STORAGE,
    models=[
        # Cirrascale deployments
        ModelEval(
            model="cirrascale-olmo-3-7b-instruct",
            tasks=[
                "humaneval:pass_at_10",
                "humaneval_plus:pass_at_10",
                "mbpp:pass_at_10",
                "mbpp_plus:pass_at_10",
                "simpleqa:judge",
                "math500:bpb",
            ],
            harness_overrides={"metrics.enabled": "true"},
        ),
        # Modal deployments
        ModelEval(
            model="modal-olmo-3-7b-instruct",
            tasks=[
                "humaneval:pass_at_10",
                "humaneval_plus:pass_at_10",
                "mbpp:pass_at_10",
                "mbpp_plus:pass_at_10",
                "simpleqa:judge",
                "math500:bpb",
            ],
            harness_overrides={"metrics.enabled": "true"},
        ),
        # Add more models as they are deployed...
    ],
)
