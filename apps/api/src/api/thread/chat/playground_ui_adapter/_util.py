from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from api.thread.chat.chat_types import ChatStreamOutput
from core.object_id import ID
from db.models.inference_opts import InferenceOpts
from db.models.message import Message

__all__ = ["Event", "RunInput", "UIMessage", "attach_message_children"]


UIMessage: TypeAlias = Message
Event: TypeAlias = ChatStreamOutput


@dataclass
class RunInput:
    all_messages: Sequence[Message]
    new_messages: Sequence[Message]
    parent_message_id: ID
    root_message_id: ID
    creator: str
    inference_opts: InferenceOpts
    model_id: str
    model_host: str


def attach_message_children(msg_chain: Sequence[Message]):
    for i, msg in enumerate(msg_chain):
        next_msg = msg_chain[i + 1] if i < len(msg_chain) - 1 else None
        if next_msg:
            msg.children = [next_msg]
            next_msg.parent = msg.id

    return msg_chain
