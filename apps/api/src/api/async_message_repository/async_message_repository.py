import abc
from collections.abc import Sequence
from itertools import groupby
from typing import Annotated, cast

from fastapi import Depends
from sqlalchemy import CursorResult, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import core.object_id as obj
from api.db.sqlalchemy_engine import SessionDependency
from api.thread.models.flat_message import FlatMessage
from api.thread.models.thread import Thread, ThreadList
from core.list_meta import ListMeta
from core.sort_options import SortDirection, SortOptions
from db.models.label import Label
from db.models.message import Message


class BaseAsyncMessageRepository(abc.ABC):
    @abc.abstractmethod
    async def add(self, message: Message) -> Message:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_messages_by_root(self, message_id: obj.ID, user_id: str) -> Sequence[Message]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_messages_by_root_for_delete(self, message_id: obj.ID) -> Sequence[Message]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_message_with_children(self, message_id: obj.ID, user_id: str) -> Sequence[Message] | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_message_by_id(
        self,
        message_id: obj.ID,
    ) -> Message | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, message: Message) -> Message:
        raise NotImplementedError

    @abc.abstractmethod
    async def soft_delete(self, message_id: obj.ID) -> None | Message:
        raise NotImplementedError

    @abc.abstractmethod
    async def soft_delete_many(self, message_ids: list[obj.ID]) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, message_id: obj.ID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_many(self, message_ids: list[obj.ID]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_threads_for_user(self, user_id: str, sort_options: SortOptions) -> ThreadList:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_thread_for_user_grouped(self, user_id: str, sort_options: SortOptions) -> ThreadList:
        raise NotImplementedError

    @abc.abstractmethod
    async def migrate_messages_to_new_user(self, previous_user_id: str, new_user_id: str) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_creator(self, creator_id: str) -> Sequence[Message]:
        raise NotImplementedError


class AsyncMessageRepository(BaseAsyncMessageRepository):
    session: AsyncSession

    def __init__(self, session: SessionDependency):
        self.session = session

    async def add(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.flush()

        query = (
            select(Message)
            .where(Message.id == message.id)
            .options(
                selectinload(Message.labels),
                selectinload(Message.tool_calls),
                selectinload(Message.tool_definitions),
            )
        )
        result = await self.session.scalars(query)
        return result.one()

    async def get_messages_by_root(self, message_id: obj.ID, user_id: str) -> Sequence[Message]:
        query = (
            select(Message)
            .where(Message.root == message_id)
            .where(
                or_(
                    Message.expiration_time == None,  # noqa: E711
                    Message.expiration_time > func.now(),
                )
            )
            .options(
                selectinload(Message.labels.and_(Label.deleted == None, Label.creator == user_id)),  # noqa: E711
                selectinload(Message.tool_calls),
                selectinload(Message.tool_definitions),
            )
            .order_by(Message.created.asc())
        )

        result = await self.session.scalars(query)

        return result.all()

    async def get_messages_by_root_for_delete(self, message_id: obj.ID) -> Sequence[Message]:
        query = select(Message).where(Message.root == message_id)

        result = await self.session.scalars(query)

        return result.all()

    async def get_message_with_children(self, message_id: obj.ID, user_id: str) -> Sequence[Message] | None:
        query = (
            select(Message)
            .where(Message.id == message_id)
            .where(
                or_(
                    Message.expiration_time == None,  # noqa: E711
                    Message.expiration_time > func.now(),
                )
            )
            .options(
                selectinload(Message.labels.and_(Label.deleted == None, Label.creator == user_id)),  # noqa: E711
                selectinload(Message.tool_calls),
                selectinload(Message.tool_definitions),
            )
        )

        result = await self.session.scalars(query)
        root_message = result.first()

        if root_message is None:
            return None

        return await self._flatten_children(root_message)

    async def _flatten_children(self, message: Message) -> Sequence[Message]:
        messages = [message]

        children = await message.awaitable_attrs.children

        for child in children or []:
            await child.awaitable_attrs.labels
            await child.awaitable_attrs.tool_calls
            await child.awaitable_attrs.tool_definitions

            child_descendants = await self._flatten_children(child)
            messages.extend(child_descendants)

        return messages

    async def get_message_by_id(self, message_id: obj.ID) -> Message | None:
        query = (
            select(Message)
            .where(Message.id == message_id)
            .where(
                or_(
                    Message.expiration_time == None,  # noqa: E711
                    Message.expiration_time > func.now(),
                )
            )
            .options(
                selectinload(Message.labels),
                selectinload(Message.tool_calls),
                selectinload(Message.tool_definitions),
            )
        )
        result = await self.session.scalars(query)
        message = result.first()

        if message is None:
            return None

        return message

    async def update(self, message: Message) -> Message:
        message_to_update = await self.session.get_one(Message, message.id)

        for var, value in vars(message).items():
            setattr(message_to_update, var, value) if value else None

        await self.session.flush()

        query = (
            select(Message)
            .where(Message.id == message.id)
            .options(
                selectinload(Message.labels),
                selectinload(Message.tool_calls),
                selectinload(Message.tool_definitions),
            )
        )
        result = await self.session.scalars(query)
        return result.one()

    async def soft_delete(self, message_id: obj.ID) -> None | Message:
        delete_stmt = update(Message).where(Message.id == message_id).values(deleted=func.now())
        delete_result = await self.session.execute(delete_stmt)

        count = cast(CursorResult, delete_result).rowcount
        if count == 0:
            return None

        # reload for eager-load relationships
        query = (
            select(Message)
            .where(Message.id == message_id)
            .options(
                selectinload(Message.labels),
                selectinload(Message.tool_calls),
                selectinload(Message.tool_definitions),
            )
        )
        result = await self.session.scalars(query)
        return result.one()

    async def soft_delete_many(self, message_ids: list[obj.ID]) -> int:
        delete_stmt = update(Message).where(Message.id.in_(message_ids)).values(deleted=func.now())
        delete_result = await self.session.execute(delete_stmt)

        count = cast(CursorResult, delete_result).rowcount

        return count

    async def delete(self, message_id: obj.ID) -> None:
        message = await self.get_message_by_id(message_id)
        if message is None:
            return
        await self.session.delete(message)

    async def delete_many(self, message_ids: list[obj.ID]) -> None:
        # cascade takes care of associations
        # except completions, which is handled separately
        await self.session.execute(delete(Message).where(Message.id.in_(message_ids)))

    async def get_threads_for_user(self, user_id: str, sort_options: SortOptions) -> ThreadList:
        thread_conditions = [
            Message.creator == user_id,
            Message.final == True,  # noqa: E712
            Message.parent == None,  # noqa: E711
            or_(Message.expiration_time == None, Message.expiration_time > func.now()),  # noqa: E711
        ]

        count_stmt = select(func.count(Message.id)).where(*thread_conditions)
        count_result = await self.session.scalars(count_stmt)
        total = count_result.one()

        select_messages = (
            select(Message)
            .where(*thread_conditions)
            .options(
                selectinload(Message.labels),
                selectinload(Message.tool_calls),
                selectinload(Message.tool_definitions),
            )
            .order_by(Message.created.desc())
        )

        # hmmm
        if sort_options.order == SortDirection.ASC:
            select_messages.order_by(None).order_by(Message.created.asc())

        if sort_options.limit is not None:
            select_messages = select_messages.limit(sort_options.limit)

        if sort_options.offset is not None:
            select_messages = select_messages.offset(sort_options.offset)

        result = await self.session.scalars(select_messages)
        thread_roots = result.all()

        threads = [Thread.from_messages(await self._flatten_children(thread)) for thread in thread_roots]

        return ThreadList(
            threads=threads,
            meta=ListMeta(total=int(total), offset=sort_options.offset, limit=sort_options.limit),
        )

    async def get_thread_for_user_grouped(self, user_id: str, sort_options: SortOptions) -> ThreadList:
        conditions = [
            Message.creator == user_id,
            Message.final == True,  # noqa: E712
            Message.parent == None,  # noqa: E711
            or_(Message.expiration_time == None, Message.expiration_time > func.now()),  # noqa: E711
        ]

        count_stmt = select(func.count(Message.id)).select_from(Message).where(*conditions)
        count_result = await self.session.scalars(count_stmt)
        total = count_result.one()

        messages_stmt = select(Message.id).where(*conditions).order_by(Message.created.desc())

        # hmmm
        if sort_options.order == SortDirection.ASC:
            messages_stmt.order_by(None).order_by(Message.created.asc())

        if sort_options.limit is not None:
            messages_stmt.limit(sort_options.limit)

        if sort_options.offset is not None:
            messages_stmt.offset(sort_options.offset)

        message_result = await self.session.scalars(messages_stmt)

        message_seq = message_result.unique().all()

        all_messages_stmt = (
            select(Message)
            .where(Message.root.in_(message_seq))
            .order_by(Message.root, Message.created)
            .options(
                selectinload(Message.labels),
                selectinload(Message.tool_calls),
                selectinload(Message.tool_definitions),
            )
        )

        all_messages_result = await self.session.scalars(all_messages_stmt)

        all_messages_seq = all_messages_result.unique().all()

        threads: list[Thread] = []
        for root_id, messages in groupby(all_messages_seq, key=lambda m: m.root):
            flat_messages = FlatMessage.from_message_seq(list(messages))
            threads.append(Thread(id=root_id, messages=flat_messages))

        return ThreadList(
            threads=threads, meta=ListMeta(total=total, offset=sort_options.offset, limit=sort_options.limit)
        )

    async def migrate_messages_to_new_user(self, previous_user_id: str, new_user_id: str):
        await self.session.execute(update(Label).where(Label.creator == previous_user_id).values(creator=new_user_id))
        result = await self.session.execute(
            update(Message)
            .where(Message.creator == previous_user_id)
            .values(creator=new_user_id, expiration_time=None, private=False)
        )
        # cast is recommended by SQLAlchemy for this: https://github.com/sqlalchemy/sqlalchemy/issues/12913
        count = cast(CursorResult, result).rowcount

        await self.session.flush()  # needed?

        return count

    async def get_by_creator(self, creator_id: str):
        query = (
            select(Message)
            .where(Message.creator == creator_id)
            .options(
                selectinload(Message.labels),
                selectinload(Message.tool_calls),
                selectinload(Message.tool_definitions),
            )
        )
        result = await self.session.scalars(query)
        return result.all()


AsyncMessageRepositoryDependency = Annotated[AsyncMessageRepository, Depends()]
