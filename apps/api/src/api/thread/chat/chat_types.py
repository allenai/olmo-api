from typing import TypeAlias

from api.thread.models.flat_message import FlatMessage
from core.message.message_chunk import Chunk, MessageChunk, MessageStreamError

ChatStreamOutput: TypeAlias = FlatMessage | MessageChunk | Chunk | MessageStreamError | None
