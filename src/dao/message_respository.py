import abc
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from src import obj
from src.api_interface import APIInterface
from src.dao import paged
from src.dao.engine_models.message import Message
from src.dao.message import ThreadList
from src.dao.paged import Opts


class ToolCall(APIInterface):
    tool_name: str
    args: str | dict[str, Any] | None = None
    tool_call_id: str


# class MessageModel(BaseModel):
#     id: obj.ID
#     content: str
#     snippet: str
#     creator: str
#     role: Role
#     opts: InferenceOpts
#     root: str
#     created: AwareDatetime
#     model_id: str
#     model_host: str
#     deleted: AwareDatetime | None = None
#     parent: str | None = None
#     template: str | None = None
#     logprobs: list[list[TokenLogProbs]] | None = None
#     children: list["FlatMessage"] | None = None
#     completion: str | None = None
#     final: bool = False
#     original: str | None = None
#     private: bool = False
#     model_type: ModelType | None = None
#     finish_reason: str | None = None
#     harmful: bool | None = None
#     expiration_time: AwareDatetime | None = None
#     labels: list[Label] = Field(default_factory=list)
#     file_urls: list[str] | None = None
#     thinking: str | None = None
#     tool_calls: list[ToolCall] | None = None


class BaseMessageRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, message: Message) -> Message:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, message_id: obj.ID) -> Message | None:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, message: Message) -> Message:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, message_id: obj.ID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_threads_for_user(self, user_id: str, sort_opts: Opts) -> ThreadList:
        raise NotImplementedError


class MessageRepository(BaseMessageRepository):
    session: Session

    def __init__(self, session: Session):
        self.session = session

    def add(self, message: Message) -> Message:
        self.session.add(message)
        self.session.flush()

        new_message = self.session.get_one(Message, message.id)
        return new_message

    def get(self, message_id: obj.ID) -> Message | None:
        return self.session.get(Message, message_id)

    def update(self, message: Message) -> Message:
        message_to_update = self.session.get_one(Message, message.id)

        for var, value in vars(message).items():
            setattr(message_to_update, var, value) if value else None

        self.session.flush()
        return message_to_update

    def delete(self, message_id: obj.ID) -> None:
        self.session.execute(delete(Message).where(Message.id == message_id))

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
