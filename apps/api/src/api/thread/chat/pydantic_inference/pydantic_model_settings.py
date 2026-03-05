from typing import Any

from pydantic_ai.models.openai import OpenAIChatModelSettings

from db.models.inference_opts import InferenceOpts
from db.models.model_config import ModelConfig


def pydantic_model_settings(
    model: ModelConfig, inference_opts: InferenceOpts, extra_body: dict[str, Any] | None
) -> OpenAIChatModelSettings:
    # Not mapping "N" from InferenceOpts

    kwargs = extra_body if extra_body is not None else {}

    return OpenAIChatModelSettings(
        max_tokens=inference_opts.max_tokens or model.max_tokens_default,
        temperature=inference_opts.temperature or model.temperature_default,
        top_p=inference_opts.top_p or model.top_p_default,
        stop_sequences=inference_opts.stop or model.stop_default or [],
        # TODO: allow changing
        openai_reasoning_effort="low" if model.can_think else None,
        extra_body=extra_body,
        # HACK: This lets us send vllm args flattened. Not sure if this is only needed for beaker queues or all, but this gets us working for now
        **kwargs
    )
