"""Full tier configuration.

Comprehensive evaluations that take longer to run.
Triggered manually, not scheduled.
"""

from evaluations.configs.base import ModelEval, StorageConfig, TierConfig, TierName

FULL_STORAGE = StorageConfig(
    s3_bucket="olmo-eval-results",
    s3_prefix="full",
    s3_group="release",
)

full_tier = TierConfig(
    name=TierName.FULL,
    description="Comprehensive evaluation suite, run sparingly",
    timeout_minutes=360,
    storage=FULL_STORAGE,
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
