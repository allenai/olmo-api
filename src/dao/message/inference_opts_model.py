from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic import Field as PydanticField

from src.api_interface import APIInterface


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
    max_tokens: int | None = PydanticField(
        default=None,
        strict=True,
    )
    temperature: float | None = PydanticField(
        default=None,
        strict=True,
    )
    n: int | None = PydanticField(default=None, strict=True)
    top_p: float | None = PydanticField(
        default=None,
        strict=True,
    )
    logprobs: int | None = PydanticField(
        default=None,
        strict=True,
    )
    stop: list[str] | None = PydanticField(default=None)

    @staticmethod
    def opts_schema() -> dict[str, Field]:
        return {f.name: f for f in [max_tokens, temperature, num, top_p, logprobs, stop]}

class InferenceOptionsConstraints(APIInterface):
    temperature_default: float | None
    temperature_upper: float | None
    temperature_lower: float | None
    temperature_step: float | None

    top_p_default: float | None
    top_p_upper: float | None
    top_p_lower: float | None
    top_p_step: float | None

    max_tokens_default: int | None
    max_tokens_upper: int | None
    max_tokens_lower: int | None
    max_tokens_step: int | None

    stop_default: list[str] | None
