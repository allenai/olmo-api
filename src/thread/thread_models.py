from dataclasses import asdict
from datetime import datetime

from pydantic import AwareDatetime, Field, computed_field

from src.api_interface import APIInterface
from src.dao import message
from src.dao.engine_models.model_config import ModelType
from src.dao.label import Rating
from src.dao.message import InferenceOpts, Message, Role
from src.inference.InferenceEngine import FinishReason


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


class FlatMessage(APIInterface):
    id: str
    content: str
    snippet: str
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
    def from_message(message: message.Message) -> list["FlatMessage"]:
        messages = [asdict(message_in_list) for message_in_list in message.flatten()]
        for message_to_change in messages:
            children = message_to_change.get("children", [])
            if children is not None:
                message_to_change["children"] = [child.get("id") for child in children]

        return [FlatMessage.model_validate(mapped_message) for mapped_message in messages]


class MessageChunkResponse(APIInterface):
    message: str
    content: str


class Thread(APIInterface):
    id: str
    messages: list[FlatMessage]

    @staticmethod
    def from_message(message: Message):
        return Thread(id=message.id, messages=FlatMessage.from_message(message))
