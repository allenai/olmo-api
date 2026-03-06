from typing import Any

from pydantic_ai.models.openai import OpenAIChatModelSettings

from db.models.inference_opts import InferenceOpts


def pydantic_model_settings(
    *, inference_opts: InferenceOpts, extra_body: dict[str, Any] | None, can_think: bool | None
) -> OpenAIChatModelSettings:
    # Not mapping "N" from InferenceOpts

    kwargs = extra_body if extra_body is not None else {}

    return OpenAIChatModelSettings(
        # these have been validated alreeady
        **inference_opts.model_dump(exclude_none=True, exclude={"stop"}),  # type: ignore
        stop_sequences=inference_opts.stop or [],
        # TODO: allow changing
        openai_reasoning_effort="low" if can_think else None,
        extra_body=extra_body,
        # HACK: This lets us send vllm args flattened. Not sure if this is only needed for beaker queues or all, but this gets us working for now
        **kwargs,  # type: ignore
    )
