from typing import TypeAlias

from api.thread.models.flat_message import FlatMessage
from core.message.message_chunk import Chunk, MessageStreamError

ChatStreamOutput: TypeAlias = FlatMessage | Chunk | MessageStreamError | None
