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
        strict=True,
    )
    temperature: float = PydanticField(
        default=temperature.default,
        strict=True,
    )
    n: int = PydanticField(
        default=num.default,
        strict=True,
    )
    top_p: float = PydanticField(
        default=top_p.default,
        strict=True,
    )
    logprobs: int | None = PydanticField(
        default=logprobs.default,
        strict=True,
    )
    stop: list[str] | None = PydanticField(default=None)

    @staticmethod
    def opts_schema() -> dict[str, Field]:
        return {f.name: f for f in [max_tokens, temperature, num, top_p, logprobs, stop]}
