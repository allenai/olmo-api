import dataclasses
import datetime
import functools
import json
import typing
from collections.abc import AsyncGenerator
from logging import getLogger
from typing import Any

from pydantic import BaseModel

from api.thread.models.thread import Thread
from db.models.message import Message


@functools.singledispatch
def encode_value(x: typing.Any) -> typing.Any:
    match x:
        case clazz if dataclasses.is_dataclass(clazz):
            return dataclasses.asdict(x)

        case BaseModel():
            return x.model_dump()

    # if dataclasses.is_dataclass(x):
    #     return dataclasses.asdict(x)  # type: ignore

    # if isinstance(x, BaseModel):

    return x


@encode_value.register(datetime.datetime)
@encode_value.register(datetime.date)
def _(x: datetime.date | datetime.datetime) -> str:
    return x.isoformat()


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

                case _:
                    yield format_message(stream_message)
    except Exception:
        getLogger().exception("Error when streaming")
        raise
