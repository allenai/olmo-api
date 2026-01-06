from core.api_interface import APIInterface
from pydantic import Field

from src.auth.auth_service import authn
from src.dao.message.message_repository import BaseMessageRepository, ThreadList
from src.dao.paged import ListMeta, Opts, SortOptions
from src.thread.thread_models import Thread


class GetThreadsRequest(SortOptions, APIInterface):
    creator: str | None = Field(default=None)
    deleted: bool = Field(default=False)


class GetThreadsResponse(APIInterface):
    threads: list[Thread]
    meta: ListMeta


def get_threads(
    request: GetThreadsRequest, message_repository: BaseMessageRepository
) -> GetThreadsResponse:
    agent = authn()

    thread_list: ThreadList

    thread_list = message_repository.get_threads_for_user(
        agent.client, Opts.from_sort_options(request)
    )
    return GetThreadsResponse(
        threads=[Thread.from_message(message) for message in thread_list.threads],
        meta=thread_list.meta,
    )
