from typing import TYPE_CHECKING

from pydantic import Field

from core.api_interface import APIInterface

if TYPE_CHECKING:
    from db.models.message import Message
    from db.models.model_config import ModelConfig


class InferenceOpts(APIInterface):
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    stop: list[str] | None = None

    # NOTE: defaults set on these two fields as they don't have defaults set in the DB model_config

    # n has a max of 1 when streaming. if we allow for non-streaming requests we can go up to 50
    n: int = Field(default=1, ge=1, le=1)
    logprobs: int | None = Field(default=None, ge=0, le=10)

    @staticmethod
    def from_message(message: "Message | None") -> "InferenceOpts | None":
        if message is None:
            return None

        # Using model_construct since we want to trust that the DB has valid data
        return InferenceOpts.model_construct(
            max_tokens=message.opts.max_tokens,
            temperature=message.opts.temperature,
            top_p=message.opts.top_p,
            stop=message.opts.stop,
            n=message.opts.n,
            logprobs=message.opts.logprobs,
        )

    @staticmethod
    def from_model_config_defaults(model_config: "ModelConfig") -> "InferenceOpts":
        return InferenceOpts.model_construct(
            max_tokens=model_config.max_tokens_default,
            temperature=model_config.temperature_default,
            top_p=model_config.top_p_default,
            stop=model_config.stop_default,
        )
