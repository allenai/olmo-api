from typing import TypeAlias

from src.dao.engine_models.message import Message
from src.dao.message.message_models import MessageStreamError
from src.message.message_chunk import (
    BaseChunk,
)

__all__ = ["StreamReturnType"]

StreamReturnType: TypeAlias = Message | MessageStreamError | BaseChunk
