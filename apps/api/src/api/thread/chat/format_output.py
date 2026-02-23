import dataclasses
import datetime
import functools
import json
import typing
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel

from api.logging.fastapi_logger import FastAPIStructLogger
from api.thread.models.thread import Thread
from db.models.message import Message

logger = FastAPIStructLogger()


# https://tomaugspurger.net/posts/serializing-dataclasses/
@functools.singledispatch
def encode_value(x: typing.Any) -> typing.Any:
    if dataclasses.is_dataclass(x):
        return dataclasses.asdict(x)  # pyright: ignore[reportArgumentType]

    return x


@encode_value.register(datetime.datetime)
@encode_value.register(datetime.date)
def format_datetime(x: datetime.date | datetime.datetime) -> str:
    return x.isoformat()


@encode_value.register(BaseModel)
def format_base_model(x: BaseModel) -> dict[str, Any]:
    return x.model_dump()


def format_message(obj) -> str:
    # indent=None forces this to output without newlines which could cause issues when parsing the output
    return json.dumps(obj=obj, default=encode_value, indent=None) + "\n"


async def format_messages(
    stream_generator: AsyncGenerator[Any],
) -> AsyncGenerator[str, Any]:
    try:
        async for stream_message in stream_generator:
            match stream_message:
                case Message():
                    flat_messages = Thread.from_message(stream_message)

                    yield format_message(flat_messages)

                case stream_message if stream_message is None:
                    ...

                case _:
                    yield format_message(stream_message)
    except Exception:
        logger.exception("Error when streaming")
        raise
