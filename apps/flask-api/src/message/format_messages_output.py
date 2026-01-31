from collections.abc import Generator
from logging import getLogger
from typing import Any

from flask import json

import src.dao.message.message_models as message
from core.api_interface import APIInterface
from core.message.message_chunk import Chunk, MessageChunk, MessageStreamError
from db.models.message import Message
from src.thread.thread_models import Thread
from src.util import CustomEncoder


def format_message(obj) -> str:
    # indent=None forces this to output without newlines which could cause issues when parsing the output
    return json.dumps(obj=obj, cls=CustomEncoder, indent=None) + "\n"


def format_messages(
    stream_generator: Generator[Message | MessageChunk | MessageStreamError | Chunk],
) -> Generator[str, Any, None]:
    try:
        for stream_message in stream_generator:
            match stream_message:
                case Message():
                    flat_messages = Thread.from_message(stream_message)

                    yield format_message(flat_messages)
                case APIInterface():
                    yield format_message(stream_message)
    except Exception:
        getLogger().exception("Error when streaming")
        raise
