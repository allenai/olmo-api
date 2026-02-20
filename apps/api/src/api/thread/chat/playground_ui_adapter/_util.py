from typing import TypeAlias

from core.message.message_chunk import BaseChunk, MessageStreamError
from db.models.message import Message

__all__ = ["StreamReturnType"]

StreamReturnType: TypeAlias = Message | MessageStreamError | BaseChunk
