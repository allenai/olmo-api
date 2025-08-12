from pydantic import Field

from src import db
from src.api_interface import APIInterface
from src.auth.auth_service import authn
from src.config.get_config import get_config
from src.dao.message_respository import MessageRepository, ThreadList
from src.dao.paged import ListMeta, Opts, SortOptions
from src.thread.thread_models import Thread


class GetThreadsRequest(SortOptions, APIInterface):
    creator: str | None = Field(default=None)
    deleted: bool = Field(default=False)


class GetThreadsResponse(APIInterface):
    threads: list[Thread]
    meta: ListMeta


def get_threads(
    dbc: db.Client, request: GetThreadsRequest, message_repository: MessageRepository
) -> GetThreadsResponse:
    agent = authn()

    thread_list: ThreadList

    if get_config().feature_flags.enable_sqlalchemy_messages:
        thread_list = message_repository.get_threads_for_user(agent.client, Opts.from_sort_options(request))
    else:
        thread_list = dbc.message.get_list(
            creator=request.creator,
            deleted=request.deleted,
            opts=Opts.from_sort_options(request),
            agent=agent.client,
        )

    return GetThreadsResponse(
        threads=[Thread.from_message(message) for message in thread_list.threads], meta=thread_list.meta
    )
