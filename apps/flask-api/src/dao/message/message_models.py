from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

import core.object_id as obj
from core.message.role import Role
from core.message.token_log_probs import TokenLogProbs
from db.models.inference_opts import InferenceOpts
from db.models.message import Message as SQLAMessage
from db.models.model_config import ModelType
from src.dao import label, paged


# OldMessage:
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
