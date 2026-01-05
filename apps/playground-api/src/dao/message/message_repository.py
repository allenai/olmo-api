import abc
from collections.abc import Sequence
from typing import cast

from sqlalchemy import CursorResult, func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from db.models.label import Label
from db.models.message import Message
from db.models.model_config import ModelType
from src import obj
from src.dao import label as old_label
from src.dao import paged
from src.dao.message.inference_opts_model import InferenceOpts
from src.dao.message.message_models import Message as OldMessage
from src.dao.message.message_models import Role, ThreadList
from src.dao.paged import Opts
from src.message.map_text_snippet import text_snippet


class BaseMessageRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, message: Message) -> Message:
        raise NotImplementedError

    @abc.abstractmethod
    def get_messages_by_root(self, message_id: obj.ID, user_id: str) -> Sequence[Message] | None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_messages_by_root_for_delete(self, message_id: obj.ID) -> Sequence[Message]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_message_with_children(self, message_id: obj.ID, user_id: str) -> Sequence[Message] | None:
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
    def soft_delete(self, message_id: obj.ID) -> None | Message:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, message_id: obj.ID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_threads_for_user(self, user_id: str, sort_opts: Opts) -> ThreadList:
        raise NotImplementedError

    @abc.abstractmethod
    def migrate_messages_to_new_user(self, previous_user_id: str, new_user_id: str) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_creator(self, creator_id: str) -> Sequence[Message]:
        raise NotImplementedError


class MessageRepository(BaseMessageRepository):
    session: Session

    def __init__(self, session: Session):
        self.session = session

    def add(self, message: Message) -> Message:
        self.session.add(message)
        self.session.flush()
        self.session.commit()

        return self.session.get_one(Message, message.id)

    def get_messages_by_root(self, message_id: obj.ID, user_id: str) -> Sequence[Message] | None:
        query = (
            select(Message)
            .where(Message.root == message_id)
            .where(
                or_(
                    Message.expiration_time == None,
                    Message.expiration_time > func.now(),
                )
            )  # noqa: E711
            .options(joinedload(Message.labels.and_(Label.deleted == None, Label.creator == user_id)))  # noqa: E711
            .order_by(Message.created.asc())
        )

        return self.session.scalars(query).unique().all()

    def get_messages_by_root_for_delete(self, message_id: obj.ID) -> Sequence[Message]:
        query = select(Message).where(Message.root == message_id)

        return self.session.scalars(query).unique().all()

    def get_message_with_children(self, message_id: obj.ID, user_id: str) -> Sequence[Message] | None:
        query = (
            select(Message)
            .where(Message.id == message_id)
            .where(
                or_(
                    Message.expiration_time == None,
                    Message.expiration_time > func.now(),
                )
            )  # noqa: E711
            .options(joinedload(Message.labels.and_(Label.deleted == None, Label.creator == user_id)))  # noqa: E711
            .order_by(Message.created.asc())
        )

        result = self.session.scalars(query).unique().all()
        if len(result) == 0:
            return None

        return self.flatten_message_children(result[0])

    def flatten_message_children(self, message: Message):
        result = [message]
        for child in message.children or []:
            result.extend(self.flatten_message_children(child))
        return result

    def get_message_by_id(self, message_id: obj.ID) -> Message | None:
        query = (
            select(Message)
            .where(Message.id == message_id)
            .where(
                or_(
                    Message.expiration_time == None,
                    Message.expiration_time > func.now(),
                )
            )  # noqa: E711
        )

        results = self.session.scalars(query).unique().all()
        if len(results) == 0:
            return None
        return results[0]

    def update(self, message: Message) -> Message:
        message_to_update = self.session.get_one(Message, message.id)

        for var, value in vars(message).items():
            setattr(message_to_update, var, value) if value else None

        self.session.flush()
        self.session.commit()
        return message_to_update

    def soft_delete(self, message_id: obj.ID) -> None | Message:
        msg = self.session.execute(
            update(Message).where(Message.id == message_id).values(deleted=func.now()).returning(Message)
        ).scalar()
        self.session.commit()
        return msg

    def delete(self, message_id: obj.ID) -> None:
        message = self.get_message_by_id(message_id)
        if message is None:
            return
        self.session.delete(message)
        self.session.commit()

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
            threads=threads,
            meta=paged.ListMeta(total=total, offset=sort_opts.offset, limit=sort_opts.limit),
        )

    def migrate_messages_to_new_user(self, previous_user_id: str, new_user_id: str):
        self.session.execute(update(Label).where(Label.creator == previous_user_id).values(creator=new_user_id))
        result = self.session.execute(
            update(Message)
            .where(Message.creator == previous_user_id)
            .values(creator=new_user_id, expiration_time=None, private=False)
        )
        # cast is recommended by SQLAlchemy for this: https://github.com/sqlalchemy/sqlalchemy/issues/12913
        count = cast(CursorResult, result).rowcount
        self.session.flush()
        self.session.commit()

        return count

    def get_by_creator(self, creator_id: str):
        query = select(Message).where(Message.creator == creator_id)
        return self.session.scalars(query).unique().all()


def map_sqla_to_old(message: Message) -> OldMessage:
    # Map message.role to old Role enum; default to user if unknown
    try:
        mapped_role = Role(message.role)
    except Exception:
        mapped_role = Role.User

    # Map model_type to old enum when possible
    try:
        mapped_model_type = ModelType(message.model_type) if message.model_type is not None else None
    except Exception:
        mapped_model_type = None

    # Build InferenceOpts without re-validation
    mapped_opts = InferenceOpts.model_construct(**message.opts)

    # We don't currently expose logprobs from ORM messages in v4 stream
    mapped_logprobs = None

    # Map labels to old label dataclass if present
    mapped_labels: list[old_label.Label] = []
    if getattr(message, "labels", None):
        for lbl in cast(list, message.labels):
            mapped_labels.append(
                old_label.Label(
                    id=lbl.id,
                    message=lbl.message,
                    rating=old_label.Rating(lbl.rating),
                    creator=lbl.creator,
                    comment=lbl.comment,
                    created=lbl.created,
                    deleted=lbl.deleted,
                )
            )

    # Map children recursively if present
    mapped_children: list[OldMessage] | None = None
    if getattr(message, "children", None):
        mapped_children = [map_sqla_to_old(child) for child in cast(list[Message], message.children)]

    return OldMessage(
        id=message.id,
        content=message.content,
        snippet=text_snippet(message.content),
        creator=message.creator,
        role=mapped_role,
        opts=mapped_opts,
        root=message.root,
        created=message.created,
        model_id=message.model_id,
        model_host=message.model_host,
        deleted=message.deleted,
        parent=message.parent,
        template=message.template,
        logprobs=mapped_logprobs,
        children=mapped_children,
        completion=message.completion,
        final=message.final,
        original=message.original,
        private=message.private,
        model_type=mapped_model_type,
        finish_reason=message.finish_reason,
        harmful=message.harmful,
        expiration_time=message.expiration_time,
        labels=mapped_labels,
        file_urls=message.file_urls,
        thinking=message.thinking,
        error_code=message.error_code,
        error_description=message.error_description,
        error_severity=message.error_severity,
    )
