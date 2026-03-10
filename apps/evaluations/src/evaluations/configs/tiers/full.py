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

LITELLM_API_BASE = "https://ai2-model-hub.allen.ai"

full_tier = TierConfig(
    name=TierName.FULL,
    description="Comprehensive evaluation suite, run sparingly",
    timeout_minutes=360,
    storage=FULL_STORAGE,
    harness_overrides={"metrics.enabled": "false"},
    models=[
        ModelEval(
            model="olmo-3-7b-instruct-cirrascale",
            provider_overrides={
                "kind": "litellm",
                "model": "litellm_proxy/openai/Olmo-3-7B-Instruct",
                "api_base": LITELLM_API_BASE,
            },
            tasks=[
                "humaneval:pass_at_10",
                "humaneval_plus:pass_at_10",
                "mbpp:pass_at_10",
                "mbpp_plus:pass_at_10",
                "math500:bpb",
            ],
        ),
        ModelEval(
            model="olmo-3-7b-instruct-modal",
            provider_overrides={
                "kind": "litellm",
                "model": "litellm_proxy/openai/ai2-release-partners/Olmo-3-7B-Instruct",
                "api_base": LITELLM_API_BASE,
            },
            tasks=[
                "humaneval:pass_at_10",
                "humaneval_plus:pass_at_10",
                "mbpp:pass_at_10",
                "mbpp_plus:pass_at_10",
                "math500:bpb",
            ],
        ),
        # Add more models as they are deployed...
    ],
)
