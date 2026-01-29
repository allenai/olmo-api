from typing import Any

from pydantic_ai.models.openai import OpenAIChatModelSettings

from db.models.inference_opts import InferenceOpts
from db.models.model_config import ModelConfig


def pydantic_settings_map(
    opts: InferenceOpts,
    model_config: ModelConfig,
    extra_body: dict[str, Any] | None = None,
) -> OpenAIChatModelSettings:
    # Not mapping "N" from InferenceOpts

    kwargs = extra_body if extra_body is not None else {}

    return OpenAIChatModelSettings(
        max_tokens=opts.max_tokens or model_config.max_tokens_default,
        temperature=opts.temperature or model_config.temperature_default,
        top_p=opts.top_p or model_config.top_p_default,
        stop_sequences=opts.stop or [],
        openai_reasoning_effort="low" if model_config.can_think else None,
        extra_body=extra_body,
        # HACK: This lets us send vllm args flattened. Not sure if this is only needed for beaker queues or all, but this gets us working for now
        **kwargs,  # type: ignore
    )
