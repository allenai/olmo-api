from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast

from pydantic import (
    AwareDatetime,
    Field,
    computed_field,
    field_serializer,
    field_validator,
)
from sqlalchemy import orm

from core.api_interface import APIInterface
from core.inference_engine.finish_reason import FinishReason
from core.label.label import Label
from core.message.message_chunk import ErrorCode, ErrorSeverity
from core.message.role import Role
from core.message.text_snippet import text_snippet
from core.tools.tool_call import ToolCall
from core.tools.tool_definition import ToolDefinition
from db.models.inference_opts import InferenceOpts
from db.models.input_parts import InputPart
from db.models.message import Message
from db.models.model_config import ModelType


class InferenceOptionsResponse(InferenceOpts, APIInterface): ...


TOOL_NAMES_TO_TRUNCATE = {
    "tulu-deep-research_serper_google_webpage_search",
    "serper_google_webpage_search",
}
CONTENT_TRUNCATION_LIMIT = 150


class FlatMessage(APIInterface):
    id: str
    content: str
    input_parts: list[InputPart] | None = Field(default=None)
    creator: str
    role: Role
    opts: InferenceOptionsResponse
    root: str
    created: AwareDatetime
    model_id: str
    model_host: str
    agent_id: str | None = Field(default=None)
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
    labels: list[Label] = Field(default_factory=list)
    file_urls: list[str] | None = Field(default=None)
    tool_calls: list[ToolCall] | None = Field(default=None)
    thinking: str | None = Field(default=None)
    tool_definitions: list[ToolDefinition] | None = Field(default=None)
    extra_parameters: dict[str, Any] | None = Field(default=None)
    error_code: ErrorCode | None = Field(default=None)
    error_description: str | None = Field(default=None)
    error_severity: ErrorSeverity | None = Field(default=None)

    @field_validator("children", mode="before")
    @classmethod
    def map_message_children_to_ids(cls, value):
        if isinstance(value, list):
            if len(value) == 0:
                return value

            if isinstance(value[0], (Message)):
                value = cast(list[Message], value)
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
    def from_message(message: Message) -> "FlatMessage":
        return FlatMessage.model_validate(message)

    @staticmethod
    def from_message_with_children(
        message: Message,
    ) -> list["FlatMessage"]:
        return _map_messages(message)

    @field_serializer("content")
    def truncate_legally_required_tool_responses(self, v: str) -> str:
        if self.role == Role.ToolResponse and any(
            tool_call.tool_name in TOOL_NAMES_TO_TRUNCATE for tool_call in self.tool_calls or []
        ):
            words = v.split(" ")
            truncated_text = " ".join(words[: CONTENT_TRUNCATION_LIMIT - 1])

            if v != truncated_text:
                # We only want to add the … if the text has been shortened
                truncated_text += "…"

            return truncated_text

        return v

    @staticmethod
    def from_message_seq(messages: Sequence[Message]) -> list["FlatMessage"]:
        for message in messages:
            children = [msg for msg in messages if msg.parent == message.id]
            orm.attributes.set_committed_value(message, "children", children)

        message_list = [FlatMessage.model_validate(message) for message in messages]
        return message_list


def _map_messages(message: Message) -> list[FlatMessage]:
    messages = [FlatMessage.from_message(message)]

    if message.children is None or len(message.children) == 0:
        return messages

    mapped_messages = [child_child for child in message.children for child_child in _map_messages(child)]
    return [*messages, *mapped_messages]
