from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from fastapi import UploadFile

from api.thread.chat.chat_types import ChatStreamOutput
from db.models.message import Message

__all__ = ["MessageAndFiles"]


MessageAndFiles: TypeAlias = tuple[Message, Sequence[UploadFile]]
MessageAndFilesList: TypeAlias = Sequence[MessageAndFiles]
# StreamInput: TypeAlias = MessageAndFilesList  # | Sequence[Message]
StreamInput: TypeAlias = Sequence[Message]


UIMessage: TypeAlias = Message
# RunInput: TypeAlias = StreamInput
Event: TypeAlias = ChatStreamOutput


@dataclass
class AgentDeps:
    new_messages: Sequence[Message]


@dataclass
class RunInput:
    all_messages: Sequence[Message]
    new_messages: Sequence[Message]
