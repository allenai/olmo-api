from pydantic import Field

from src import db
from src.api_interface import APIInterface
from src.auth.auth_service import authn
from src.dao.paged import ListMeta, Opts, SortOptions
from src.thread.thread_models import Thread


class GetThreadsRequest(SortOptions, APIInterface):
    creator: str | None = Field(default=None)
    deleted: bool = Field(default=False)


class GetThreadsResponse(APIInterface):
    threads: list[Thread]
    meta: ListMeta


def get_threads(dbc: db.Client, request: GetThreadsRequest) -> GetThreadsResponse:
    agent = authn()

    message_list = dbc.message.get_list(
        creator=request.creator,
        deleted=request.deleted,
        opts=Opts.from_sort_options(request),
        agent=agent.client,
    )

    return GetThreadsResponse(
        threads=[Thread.from_message(message) for message in message_list.messages], meta=message_list.meta
    )
