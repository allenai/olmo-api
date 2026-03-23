"""Standard tier configuration.

Curated standard evaluations that run multiple days per week to weekly.
Should complete in 1-2 hours.
"""

from evaluations.configs.base import ModelEval, StorageConfig, TierConfig, TierName
from evaluations.settings import settings

STANDARD_STORAGE = StorageConfig(
    s3_bucket="ai2-paull",
    s3_prefix="olmo-eval",
    s3_group="standard",
)

standard_tier = TierConfig(
    name=TierName.STANDARD,
    description="Curated standard evaluations, 1-2 hours",
    timeout_minutes=120,
    storage=STANDARD_STORAGE,
    harness_overrides={"metrics.enabled": "true"},
    schedule="0 2 * * 1,4",  # Monday and Thursday at 2am UTC
    models=[
        ModelEval(
            model="olmo-3-7b-instruct-cirrascale",  # display name
            provider_overrides={
                "kind": "litellm",
                "model": "litellm_proxy/openai/Olmo-3-7B-Instruct",
                "api_base": settings.LITELLM_API_BASE,
            },
            tasks=[
                "humaneval:bpb",
            ],
            task_overrides={"limit": "10"},
        ),
        ModelEval(
            model="olmo-3-7b-instruct-modal",  # display name
            provider_overrides={
                "kind": "litellm",
                "model": "litellm_proxy/openai/ai2-release-partners/Olmo-3-7B-Instruct",
                "api_base": settings.LITELLM_API_BASE,
            },
            tasks=[
                "humaneval:bpb",
            ],
            task_overrides={"limit": "10"},
        ),
        # Add more models as they are deployed...
    ],
)
