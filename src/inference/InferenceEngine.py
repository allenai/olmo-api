from abc import abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Generator, Optional, Protocol, Sequence

from werkzeug.datastructures import FileStorage

from src import config


class FinishReason(StrEnum):
    # Something caused the generation to be left incomplete. The only scenario where this happens
    # (that we know of) is when the prompt is too long and it's the only item being process (batch
    # size is 1):
    # See: https://github.com/allenai/inferd-tulu2/blob/main/src/svllm.py#L106
    UnclosedStream = "unclosed stream"

    # The model stopped because max_tokens was reached, or because the prompt was too long and
    # there were several items in the batch.
    Length = "length"

    # The model generated a response and stopped before max_tokens was reached.
    Stop = "stop"

    # The generation was aborted for an unknown reason.
    Aborted = "aborted"


@dataclass
class BaseInferenceEngineMessage:
    role: str
    content: str


@dataclass
class InferenceEngineMessageWithFiles(BaseInferenceEngineMessage):
    # We may want to make this generic to "files" later? Need to figure out how to handle extensions and file type checking.
    files: Sequence[FileStorage | str]


@dataclass
class Logprob:
    token_id: int
    text: str
    logprob: float


@dataclass
class InferenceEngineChunk:
    content: str
    finish_reason: Optional[FinishReason] = None
    id: Optional[str] = None
    created: Optional[str] = None
    model: Optional[str] = None
    logprobs: Sequence[Sequence[Logprob]] = field(default_factory=list)
    input_token_count: int = -1
    output_token_count: int = -1


@dataclass
class InferenceOptions(Protocol):
    max_tokens: int = 2048
    temperature: float = 1.0
    n: int = 1
    top_p: float = 1.0
    logprobs: Optional[int] = None
    stop: Optional[list[str]] = None


class InferenceEngine(Protocol):
    @abstractmethod
    def get_model_details(self, model_id: str) -> config.Model | None:
        raise NotImplementedError

    @abstractmethod
    def create_streamed_message(
        self,
        model: str,
        messages: Sequence[BaseInferenceEngineMessage],
        inference_options: InferenceOptions,
    ) -> Generator[InferenceEngineChunk, None, None]:
        raise NotImplementedError
