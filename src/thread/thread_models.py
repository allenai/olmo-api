from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast

from pydantic import AwareDatetime, Field, computed_field, field_validator

from src.api_interface import APIInterface
from src.dao.engine_models.message import Message as SQLAMessage
from src.dao.engine_models.model_config import ModelType
from src.dao.engine_models.tool_definitions import ToolSource
from src.dao.label import Rating
from src.dao.message.message_models import InferenceOpts, Message, Role
from src.inference.InferenceEngine import FinishReason
from src.message.map_text_snippet import text_snippet


class LabelResponse(APIInterface):
    id: str
    message: str
    rating: Rating
    creator: str
    comment: str | None = Field(default=None)
    created: AwareDatetime
    deleted: AwareDatetime | None = Field(default=None)


class InferenceOptionsResponse(InferenceOpts, APIInterface): ...


class LogProbResponse(APIInterface):
    token_id: int
    text: str
    logprob: float


class ToolCall(APIInterface):
    tool_name: str
    args: str | dict[str, Any] | None = None
    tool_call_id: str
    tool_source: ToolSource


class ToolDefinition(APIInterface):
    name: str
    description: str
    parameters: dict[str, Any] | None = None
    tool_source: ToolSource


class FlatMessage(APIInterface):
    id: str
    content: str
    creator: str
    role: Role
    opts: InferenceOptionsResponse
    root: str
    created: AwareDatetime
    model_id: str
    model_host: str
    deleted: AwareDatetime | None = Field(default=None)
    parent: str | None = Field(default=None)
    template: str | None = Field(default=None)
    children: list[str] | None = Field(default=None)
    completion: str | None = Field(default=None)
    final: bool = Field(default=False)
    original: str | None = Field(default=None)
    private: bool = Field(default=False)
    model_type: ModelType | None = None
    finish_reason: FinishReason | None = None
    harmful: bool | None = None
    expiration_time: AwareDatetime | None = Field(default=None)
    labels: list[LabelResponse] = Field(default_factory=list)
    file_urls: list[str] | None = Field(default=None)
    tool_calls: list[ToolCall] | None = Field(default=None)
    thinking: str | None = Field(default=None)
    tool_definitions: list[ToolDefinition] | None = Field(default=None)

    @field_validator("children", mode="before")
    @classmethod
    def map_message_children_to_ids(cls, value):
        if isinstance(value, list):
            if len(value) == 0:
                return value

            if isinstance(value[0], (Message, SQLAMessage)):
                value = cast(list[Message] | list[SQLAMessage], value)
                return [child.id for child in value]

        return value

    @computed_field  # type:ignore
    @property
    def snippet(self) -> str:
        return text_snippet(self.content)

    @computed_field  # type:ignore
    @property
    def is_limit_reached(self) -> bool:
        return self.finish_reason == FinishReason.Length

    @computed_field  # type:ignore
    @property
    def is_older_than_30_days(self) -> bool:
        time_since_creation = datetime.now(tz=self.created.tzinfo) - self.created
        return time_since_creation.days > 30  # noqa: PLR2004

    @staticmethod
    def from_message(message: Message | SQLAMessage) -> "FlatMessage":
        return FlatMessage.model_validate(message)

    @staticmethod
    def from_message_with_children(message: Message | SQLAMessage) -> list["FlatMessage"]:
        return _map_messages(message)


def _map_messages(message: Message | SQLAMessage) -> list[FlatMessage]:
    messages = [FlatMessage.from_message(message)]

    if message.children is None or len(message.children) == 0:
        return messages

    mapped_messages = [child_child for child in message.children for child_child in _map_messages(child)]
    return [*messages, *mapped_messages]


class Thread(APIInterface):
    id: str
    messages: list[FlatMessage]

    @staticmethod
    def from_message(message: Message | SQLAMessage) -> "Thread":
        messages = FlatMessage.from_message_with_children(message)

        return Thread(id=message.id, messages=messages)

    @staticmethod
    def from_messages(messages: Sequence[SQLAMessage]) -> "Thread":
        mapped_messages = [FlatMessage.from_message(message) for message in messages]

        return Thread(id=mapped_messages[0].id, messages=mapped_messages)
