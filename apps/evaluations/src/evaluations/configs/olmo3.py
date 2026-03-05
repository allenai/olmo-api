"""Evaluation job configurations for OLMo 3 models."""

from evaluations.configs.base import EvalJobConfig

# OLMo 3 7B Instruct - HumanEval BPB evaluation
olmo3_7b_humaneval_bpb = EvalJobConfig(
    name="olmo3-7b-humaneval-bpb",
    model="cirrascale-olmo-3-7b-instruct",
    task="humaneval:bpb",
    harness="default",
    limit=20,
    overrides={
        "metrics.enabled": "true",
    },
    required_env_vars=["LITELLM_PROXY_API_KEY"],
)

# Add more OLMo 3 evaluation configs here as needed
