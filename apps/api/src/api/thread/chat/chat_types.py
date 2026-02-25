from typing import TypeAlias

from core.message.message_chunk import Chunk, MessageStreamError
from db.models.message import Message

ChatStreamOutput: TypeAlias = Message | Chunk | MessageStreamError
