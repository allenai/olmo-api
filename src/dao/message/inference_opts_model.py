from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.dao.engine_models.message import Message


class InferenceOpts(BaseModel):
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
            max_tokens=message.opts.get("max_tokens", None),
            temperature=message.opts.get("temperature", None),
            top_p=message.opts.get("top_p", None),
            stop=message.opts.get("stop", None),
            n=message.opts.get("n", None),
            logprobs=message.opts.get("logprobs", None),
        )
