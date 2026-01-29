from abc import abstractmethod
from collections.abc import Generator, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from werkzeug.datastructures import FileStorage

from core.inference_engine.finish_reason import FinishReason


@dataclass
class InferenceEngineMessage:
    role: str
    content: str
    files: Sequence[FileStorage | str] | None = None


@dataclass
class Logprob:
    token_id: int
    text: str
    logprob: float


@dataclass
class InferenceEngineChunk:
    content: str
    finish_reason: FinishReason | None = None
    id: str | None = None
    created: str | None = None
    model: str | None = None
    logprobs: Sequence[Sequence[Logprob]] = field(default_factory=list)
    input_token_count: int = -1
    output_token_count: int = -1


@dataclass
class InferenceOptions:
    max_tokens: int = 2048
    temperature: float = 1.0
    n: int = 1
    top_p: float = 1.0
    logprobs: int | None = None
    stop: list[str] | None = None


class InferenceEngine(Protocol):
    @abstractmethod
    def create_streamed_message(
        self,
        model: str,
        messages: Sequence[InferenceEngineMessage],
        inference_options: InferenceOptions,
    ) -> Generator[InferenceEngineChunk, None, None]:
        raise NotImplementedError
