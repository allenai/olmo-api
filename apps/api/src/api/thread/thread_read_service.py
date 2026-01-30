from typing import Annotated

from fastapi import Depends

from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.db.sqlalchemy_engine import SessionDependency
from api.thread.models.flat_message import FlatMessage
from api.thread.models.thread import Thread, ThreadList
from core.sort_options import SortOptions


class ThreadReadService:
    def __init__(self, session: SessionDependency, message_repository: AsyncMessageRepositoryDependency):
        self.session = session
        self.message_repository = message_repository

    async def get_all_for_user(self, user_id: str, sort_options: SortOptions) -> ThreadList:
        async with self.session.begin():
            return await self.message_repository.get_threads_for_user(user_id=user_id, sort_options=sort_options)

    async def get_one_with_user(self, thread_id: str, user_id: str) -> Thread | None:
        async with self.session.begin():
            messages_seq = await self.message_repository.get_message_with_children(message_id=thread_id, user_id=user_id)

            if messages_seq is None:
                return None

            if len(messages_seq) == 0:
                return None

            return Thread.from_messages(messages_seq)

    # Alternate versions
    async def get_all_for_user_grouped(self, user_id: str, sort_options: SortOptions) -> ThreadList:
        async with self.session.begin():
            return await self.message_repository.get_thread_for_user_grouped(user_id=user_id, sort_options=sort_options)

    async def get_root_with_user(self, thread_id: str, user_id: str) -> Thread | None:
        async with self.session.begin():
            messages_seq = await self.message_repository.get_messages_by_root(message_id=thread_id, user_id=user_id)

            if messages_seq is None:
                return None

            if len(messages_seq) == 0:
                return None

            messages = FlatMessage.from_message_seq(messages_seq)

            return Thread(id=messages[0].id, messages=messages)


ThreadReadServiceDependency = Annotated[ThreadReadService, Depends()]
