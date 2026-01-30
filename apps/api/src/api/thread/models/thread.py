from collections.abc import Sequence

from api.thread.models.flat_message import FlatMessage
from core.api_interface import APIInterface
from core.list_meta import ListMeta
from db.models.message import Message


class Thread(APIInterface):
    id: str
    messages: list[FlatMessage]

    @staticmethod
    def from_message(message: Message) -> "Thread":
        messages = FlatMessage.from_message_with_children(message)

        return Thread(id=message.id, messages=messages)

    @staticmethod
    def from_messages(messages: Sequence[Message]) -> "Thread":
        mapped_messages = [FlatMessage.model_validate(message) for message in messages]
        return Thread(id=messages[0].id, messages=mapped_messages)


class ThreadList(APIInterface):
    threads: list[Thread]
    meta: ListMeta
