from pydantic import Field

from src import db
from src.api_interface import APIInterface
from src.auth.auth_service import authn
from src.dao.message import Message
from src.dao.paged import Opts, SortOptions
from src.message.message_response_models import FlatMessage


class GetMessagesRequest(SortOptions, APIInterface):
    creator: str | None = Field(default=None)
    deleted: bool = Field(default=False)


class Thread(APIInterface):
    id: str
    messages: list[FlatMessage]

    @staticmethod
    def from_message(message: Message):
        return Thread(id=message.id, messages=FlatMessage.from_message(message))


class GetMessagesResponse(APIInterface):
    messages: list[Thread]


def get_messages(dbc: db.Client, request: GetMessagesRequest) -> GetMessagesResponse:
    agent = authn()

    message_list = dbc.message.get_list(
        creator=request.creator,
        deleted=request.deleted,
        opts=Opts.from_sort_options(request),
        agent=agent.client,
    )

    return GetMessagesResponse(messages=[Thread.from_message(message) for message in message_list.messages])
