from collections.abc import Sequence
from typing import Annotated, Any, Literal, Self

from fastapi import UploadFile
from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    Json,
    computed_field,
    field_validator,
    model_validator,
)

from api.config import settings
from core.api_interface import APIInterface
from core.message.role import Role
from db.models.inference_opts import InferenceOpts
from db.models.input_parts import InputPart, PointPartType


class ParameterDef(APIInterface):
    type: str
    properties: dict[str, "ParameterDef"] | None = Field(default=None)
    description: str | None = Field(default=None)
    required: list[str] | None = Field(default=[])
    property_ordering: list[str] | None = Field(default=None)
    default: dict[str, str] | None = Field(default=None)


class CreateToolDefinition(APIInterface):
    name: str
    description: str
    parameters: ParameterDef


def captcha_token_required_on_prod(value: str | None):
    if settings.ENV.is_production and value is None:
        msg = "Failed to evaluate captcha. Please reload the page and try again."
        raise ValueError(msg)

    return value


def ensure_list(value: Any) -> Any:
    if value is not None and not isinstance(value, list):
        return [value]

    return value


class BaseChatRequest(APIInterface):
    model: str
    host: str | None = Field(default=None, deprecated=True)

    template: str | None = Field(default=None)
    private: bool = Field(default=False)

    bypass_safety_check: bool = Field(default=False)

    captcha_token: Annotated[str | None, AfterValidator(captcha_token_required_on_prod)] = Field(default=None)

    max_tokens: int | None = Field(default=None)
    temperature: float | None = Field(default=None)
    top_p: float | None = Field(default=None)
    stop: Annotated[list[str] | None, BeforeValidator(ensure_list)] = Field(default_factory=list)
    n: int | None = Field(default=1, ge=1, le=1)
    logprobs: int | None = Field(default=None, ge=0, le=10)
    extra_parameters: Json[dict[str, Any]] | None = Field(default=None)

    files: Annotated[Sequence[UploadFile] | None, BeforeValidator(ensure_list)] = Field(default=None)

    tool_definitions: Json[list[CreateToolDefinition]] | None = Field(default=None)
    selected_tools: Annotated[list[str] | None, BeforeValidator(ensure_list)] = Field(default=None)
    enable_tool_calling: bool = Field(default=False)

    @computed_field
    @property
    def inference_options(self) -> InferenceOpts:
        return InferenceOpts(max_tokens=self.max_tokens, temperature=self.temperature, top_p=self.top_p, stop=self.stop)


class ContentChatRequest(BaseChatRequest):
    content: str | None = Field(default=None)
    input_parts: Annotated[list[Json[InputPart]] | None, BeforeValidator(ensure_list)] = Field(default=None)

    @field_validator("content", mode="after")
    @classmethod
    def standardize_newlines(cls, value: str | None) -> str | None:
        if value is None:
            return value

        return value.replace("\r\n", "\n")

    @field_validator("input_parts", mode="after")
    @classmethod
    def only_one_molmo_2_input_part_allowed(cls, value: list[InputPart] | None) -> list[InputPart] | None:
        if value is None:
            return value

        molmo_2_point_parts = [part for part in value if part.type == PointPartType.MOLMO_2_INPUT_POINT]
        if len(molmo_2_point_parts) > 1:
            msg = "Only one Molmo 2 input part allowed per request"
            raise ValueError(msg)

        return value

    @model_validator(mode="after")
    def one_of_input_parts_or_content_is_present(self) -> Self:
        if not self.content and not self.input_parts:
            msg = "One of content or inputParts is required"
            raise ValueError(msg)

        return self


class UserChatRequest(ContentChatRequest):
    role: Literal[Role.User] = Role.User
    parent: str | None = Field(default=None)

    original: str | None = Field(default=None)

    @model_validator(mode="after")
    def check_original_and_parent_are_different(self) -> Self:
        if self.original is not None and self.parent == self.original:
            msg = "The original message cannot also be the parent"
            raise ValueError(msg)

        return self


class AssistantChatRequest(ContentChatRequest):
    role: Literal[Role.Assistant]
    parent: str


class ToolResponseChatRequest(BaseChatRequest):
    role: Literal[Role.ToolResponse] = Role.ToolResponse
    parent: str
    tool_call_id: str
    content: str


CHAT_REQUEST_DISCRIMINATOR = "role"

ChatRequest = Annotated[
    UserChatRequest | AssistantChatRequest | ToolResponseChatRequest,
    Field(discriminator=CHAT_REQUEST_DISCRIMINATOR),
]
