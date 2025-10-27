from collections.abc import Generator
from logging import getLogger
from typing import Any

import src.dao.message.message_models as message
from src.api_interface import APIInterface
from src.dao.engine_models.message import Message
from src.message.create_message_service.endpoint import format_message
from src.message.message_chunk import Chunk
from src.thread.thread_models import Thread


def format_messages(
    stream_generator: Generator[Message | message.MessageChunk | message.MessageStreamError | Chunk],
) -> Generator[str, Any, None]:
    try:
        for stream_message in stream_generator:
            match stream_message:
                case Message():
                    flat_messages = Thread.from_message(stream_message)

                    yield format_message(flat_messages)
                case APIInterface():
                    yield format_message(stream_message)
    except Exception as e:
        getLogger().exception("Error when streaming")
        raise e
