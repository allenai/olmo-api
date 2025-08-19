import abc
from collections.abc import Sequence

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from src import obj
from src.dao import paged
from src.dao.engine_models.label import Label
from src.dao.engine_models.message import Message
from src.dao.message.message_models import ThreadList
from src.dao.paged import Opts


class BaseMessageRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, message: Message) -> Message:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, message_id: obj.ID, user_id: str) -> Sequence[Message] | None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_message_by_id(
        self,
        message_id: obj.ID,
    ) -> Message | None:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, message: Message) -> Message:
        raise NotImplementedError

    @abc.abstractmethod
    def soft_delete(self, message_id: obj.ID) -> Message | None:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, message_id: obj.ID) -> Message | None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_threads_for_user(self, user_id: str, sort_opts: Opts) -> ThreadList:
        raise NotImplementedError

    @abc.abstractmethod
    def migrate_messages_to_new_user(self, previous_user_id: str, new_user_id: str) -> int:
        raise NotImplementedError


class MessageRepository(BaseMessageRepository):
    session: Session

    def __init__(self, session: Session):
        self.session = session

    def add(self, message: Message) -> Message:
        self.session.add(message)
        self.session.flush()

        return self.session.get_one(Message, message.id)

    def get(self, message_id: obj.ID, user_id: str) -> Sequence[Message] | None:
        query = (
            select(Message)
            .where(Message.root == message_id)
            .where(or_(Message.expiration_time == None, Message.expiration_time > func.now()))  # noqa: E711
            .options(joinedload(Message.labels.and_(Label.deleted == None, Label.creator == user_id)))  # noqa: E711
            .order_by(Message.created.asc())
        )

        return self.session.scalars(query).unique().all()

    def get_message_by_id(
        self,
        message_id: obj.ID,
    ):
        query = (
            select(Message)
            .where(Message.root == message_id)
            .where(or_(Message.expiration_time == None, Message.expiration_time > func.now()))  # noqa: E711
        )

        results = self.session.scalars(query).unique().all()
        return results[0]

    def update(self, message: Message) -> Message:
        message_to_update = self.session.get_one(Message, message.id)

        for var, value in vars(message).items():
            setattr(message_to_update, var, value) if value else None

        self.session.flush()
        return message_to_update

    def soft_delete(self, message_id: obj.ID) -> Message | None:
        return self.session.execute(
            update(Message).where(Message.id == message_id).values(deleted=func.now()).returning(Message)
        ).scalar()

    def delete(self, message_id: obj.ID) -> Message | None:
        return self.session.execute(delete(Message).where(Message.id == message_id).returning(Message)).scalar()

    def get_threads_for_user(self, user_id: str, sort_opts: Opts) -> ThreadList:
        thread_conditions = [
            Message.creator == user_id,
            Message.final == True,  # noqa: E712
            Message.parent == None,  # noqa: E711
            or_(Message.expiration_time == None, Message.expiration_time > func.now()),  # noqa: E711
        ]

        total = self.session.query(Message.id).where(*thread_conditions).count()

        select_messages = select(Message).where(*thread_conditions).order_by(Message.created.desc())

        if sort_opts.limit is not None:
            select_messages = select_messages.limit(sort_opts.limit)

        if sort_opts.offset is not None:
            select_messages = select_messages.offset(sort_opts.offset)

        threads = self.session.scalars(select_messages).unique().all()

        return ThreadList(
            threads=threads, meta=paged.ListMeta(total=total, offset=sort_opts.offset, limit=sort_opts.limit)
        )

    def migrate_messages_to_new_user(self, previous_user_id: str, new_user_id: str):
        self.session.execute(update(Label).where(Label.creator == previous_user_id).values(creator=new_user_id))
        count = self.session.execute(
            update(Message)
            .where(Message.creator == previous_user_id)
            .values(creator=new_user_id, expiration_time=None, private=False)
        ).rowcount
        self.session.flush()

        return count
