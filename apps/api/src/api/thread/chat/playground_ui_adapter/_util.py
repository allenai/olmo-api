from collections.abc import Sequence
from typing import TypeAlias

from fastapi import UploadFile

from api.thread.models.thread import Thread
from core.message.message_chunk import BaseChunk, MessageStreamError
from db.models.message import Message

__all__ = ["MessageAndFiles", "StreamReturnType"]


MessageAndFiles: TypeAlias = tuple[Message, Sequence[UploadFile]]
MessageAndFilesList: TypeAlias = Sequence[MessageAndFiles]

StreamReturnType: TypeAlias = Thread | MessageStreamError | BaseChunk
