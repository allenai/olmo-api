"""Smoke tier configuration.

Quick sanity checks that run multiple times per day to daily.
Should complete in under 1 hour with simple pass/fail results.
"""

from evaluations.configs.base import ModelEval, StorageConfig, TierConfig, TierName
from evaluations.settings import settings

SMOKE_STORAGE = StorageConfig(
    s3_bucket="ai2-paull",
    s3_prefix="olmo-eval",
    s3_group="smoke",
)

smoke_tier = TierConfig(
    name=TierName.SMOKE,
    description="Quick sanity checks, simple pass/fail, <1 hour",
    timeout_minutes=60,
    storage=SMOKE_STORAGE,
    harness_overrides={"metrics.enabled": "false"},
    schedule=None,  # "0 */6 * * *",  # Every 6 hours
    models=[
        ModelEval(
            model="olmo-3-7b-instruct-cirrascale",
            provider_overrides={
                "kind": "litellm",
                "model": "litellm_proxy/openai/Olmo-3-7B-Instruct",
                "api_base": settings.LITELLM_API_BASE,
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
                "api_base": settings.LITELLM_API_BASE,
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
