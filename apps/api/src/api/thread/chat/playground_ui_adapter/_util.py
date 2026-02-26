from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from api.thread.chat.chat_types import ChatStreamOutput
from core.object_id import ID
from db.models.message import Message

__all__ = ["Event", "RunInput", "UIMessage"]


UIMessage: TypeAlias = Message
Event: TypeAlias = ChatStreamOutput


@dataclass
class RunInput:
    all_messages: Sequence[Message]
    new_messages: Sequence[Message]
    parent_message_id: ID
    root_message_id: ID
