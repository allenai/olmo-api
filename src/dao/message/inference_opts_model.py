from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic import Field as PydanticField


@dataclass
class Field:
    name: str
    default: Any
    min: Any
    max: Any
    step: int | float | None = None


max_tokens = Field("max_tokens", 2048, 1, 2048, 1)
temperature = Field("temperature", 0.7, 0.0, 1.0, 0.01)
# n has a max of 1 when streaming. if we allow for non-streaming requests we can go up to 50
num = Field("n", 1, 1, 1, 1)
top_p = Field("top_p", 1.0, 0.01, 1.0, 0.01)
logprobs = Field("logprobs", None, 0, 10, 1)
stop = Field("stop", None, None, None)

class InferenceOpts(BaseModel):
    max_tokens: int = PydanticField(
        default=max_tokens.default,
        ge=max_tokens.min,
        le=max_tokens.max,
        multiple_of=max_tokens.step,
        strict=True,
    )
    temperature: float = PydanticField(
        default=temperature.default,
        ge=temperature.min,
        le=temperature.max,
        multiple_of=temperature.step,
        strict=True,
    )
    n: int = PydanticField(default=num.default, ge=num.min, le=num.max, multiple_of=num.step, strict=True)
    top_p: float = PydanticField(
        default=top_p.default,
        ge=top_p.min,
        le=top_p.max,
        multiple_of=top_p.step,
        strict=True,
    )
    logprobs: int | None = PydanticField(
        default=logprobs.default,
        ge=logprobs.min,
        le=logprobs.max,
        multiple_of=logprobs.step,
        strict=True,
    )
    stop: list[str] | None = PydanticField(default=stop.default)

    @staticmethod
    def get_defaults() -> dict[str, Any]:
        return {f.name: f.default for f in [max_tokens, temperature, num, top_p, logprobs, stop]}

    @staticmethod
    def opts_schema() -> dict[str, Field]:
        return {f.name: f for f in [max_tokens, temperature, num, top_p, logprobs, stop]}

    @staticmethod
    def from_request(request_opts: dict[str, Any]) -> "InferenceOpts":
        return InferenceOpts(**request_opts)
