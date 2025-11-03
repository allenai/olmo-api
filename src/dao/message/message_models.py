from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from src import obj
from src.api_interface import APIInterface
from src.dao import label, paged
from src.dao.engine_models.message import Message as SQLAMessage
from src.dao.engine_models.model_config import ModelType
from src.dao.message.inference_opts_model import InferenceOpts


class ToolCall(APIInterface):
    tool_name: str
    args: str | dict[str, Any] | None = None
    tool_call_id: str


class Role(StrEnum):
    User = "user"
    Assistant = "assistant"
    System = "system"
    ToolResponse = "tool_call_result"


@dataclass
class TokenLogProbs:
    token_id: int
    text: str
    logprob: float


class MessageChunk(APIInterface):
    message: obj.ID
    content: str
    logprobs: list[list[TokenLogProbs]] | None = None


class MessageStreamError(APIInterface):
    message: obj.ID
    error: str
    reason: str


@dataclass
class Message:
    id: obj.ID
    content: str
    snippet: str
    creator: str
    role: Role
    opts: InferenceOpts
    root: str
    created: datetime
    model_id: str
    model_host: str
    deleted: datetime | None = None
    parent: str | None = None
    template: str | None = None
    logprobs: list[list[TokenLogProbs]] | None = None
    children: list["Message"] | None = None
    completion: str | None = None
    final: bool = False
    original: str | None = None
    private: bool = False
    model_type: ModelType | None = None
    finish_reason: str | None = None
    harmful: bool | None = None
    expiration_time: datetime | None = None
    labels: list[label.Label] = field(default_factory=list)
    file_urls: list[str] | None = None
    thinking: str | None = None
    error_code: str | None = None
    error_description: str | None = None
    error_severity: str | None = None


@dataclass
class MessageList(paged.List):
    messages: list[Message]


@dataclass
class ThreadList:
    threads: Sequence[SQLAMessage] | Sequence[Message]
    meta: paged.ListMeta
