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

LITELLM_API_BASE = "https://ai2-model-hub.allen.ai"

smoke_tier = TierConfig(
    name=TierName.SMOKE,
    description="Quick sanity checks, simple pass/fail, <1 hour",
    timeout_minutes=60,
    storage=SMOKE_STORAGE,
    models=[
        ModelEval(
            model="olmo-3-7b-instruct-cirrascale",
            provider_overrides={
                "kind": "litellm",
                "model": "litellm_proxy/openai/Olmo-3-7B-Instruct",
                "api_base": LITELLM_API_BASE,
            },
            tasks=[
                "smoke_identity_olmo",
                "smoke_hello",
                "smoke_tools",
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
                "smoke_identity_olmo",
                "smoke_hello",
                "smoke_tools",
            ],
        ),
        # Add more models as they are deployed...
    ],
)
