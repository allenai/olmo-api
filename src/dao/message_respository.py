import abc
from typing import Any

from sqlalchemy.orm import Session

from src import obj
from src.api_interface import APIInterface
from src.dao.engine_models.message import Message
from src.thread.thread_models import FlatMessage


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
    def add(self, message: FlatMessage) -> FlatMessage:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, message_id: obj.ID) -> FlatMessage | None:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, message: FlatMessage) -> FlatMessage:
        raise NotImplementedError

    @abc.abstractmethod
    def remove(self, message_id: obj.ID) -> None:
        raise NotImplementedError


def map_flat_message_to_message(message: FlatMessage) -> Message:
    return Message(
        id=message.id,
        content=message.content,
        creator=message.creator,
        role=message.role,
        opts=message.opts.model_dump(),
        root=message.root,
        created=message.created,
        final=message.final,
        private=message.private,
        model_id=message.model_id,
        model_host=message.model_host,
        model_type=message.model_type,
        deleted=message.deleted,
        parent=message.parent,
        template=message.template,
        logprobs=None,
        completion=message.completion,
        original=message.original,
        finish_reason=message.finish_reason,
        harmful=message.harmful,
        expiration_time=message.expiration_time,
        file_urls=message.file_urls,
    )


class MessageRepository(BaseMessageRepository):
    session: Session

    def __init__(self, session: Session):
        self.session = session

    def add(self, message: FlatMessage) -> FlatMessage:
        message_to_add = map_flat_message_to_message(message)
        self.session.add(message_to_add)
        self.session.commit()

        new_message = self.session.get_one(Message, message.id)
        return FlatMessage.from_message(new_message)

    def get(self, message_id: obj.ID) -> FlatMessage | None:
        message = self.session.get(Message, message_id)

        if message is None:
            return None

        return FlatMessage.from_message(message)

    def update(self, message: FlatMessage) -> FlatMessage:
        message_to_update = self.session.get_one(Message, message.id)

        for var, value in vars(message).items():
            setattr(message_to_update, var, value) if value else None

        self.session.commit()
        return FlatMessage.from_message(message_to_update)
