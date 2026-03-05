from typing import TypeAlias

from core.message.message_chunk import Chunk, MessageStreamError

ChatStreamOutput: TypeAlias = Chunk | MessageStreamError
