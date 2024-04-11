from abc import abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Generator, List, Optional, Protocol

from src.dao import message


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
class InferenceEngineMessage:
    role: message.Role
    content: str


@dataclass
class InferenceEngineChunk:
    content: str
    finish_reason: Optional[FinishReason] = None
    id: Optional[str] = None
    created: Optional[str] = None
    model: Optional[str] = None
    logprobs: Optional[float] = None


class InferenceEngine(Protocol):
    @abstractmethod
    def create_streamed_message(
        self,
        model: str,
        messages: List[InferenceEngineMessage],
        max_tokens: Optional[int] = None,
        stop_words: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        logprobs: Optional[int] = None,
    ) -> Generator[InferenceEngineChunk, None, None]:
        raise NotImplementedError
