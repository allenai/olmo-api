from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Any, Literal, Self, TypeAlias

from pydantic import AfterValidator, BaseModel, Field, Json, field_validator, model_validator
from werkzeug import exceptions

from src.api_interface import APIInterface
from src.config.get_config import get_config
from src.dao.engine_models.message import Message

# We import PromptTemplate and ToolDefinition so Pydantic knows how to resolve them, preventing some model definition errors
from src.dao.engine_models.prompt_template import PromptTemplate  # noqa: F401
from src.dao.engine_models.tool_definitions import ToolDefinition  # noqa: F401
from src.dao.message.inference_opts_model import (
    InferenceOpts,
)
from src.dao.message.message_models import Role
from src.flask_pydantic_api.utils import UploadedFile


def captcha_token_required_if_captcha_enabled(value: str | None):
    if get_config().google_cloud_services.require_recaptcha and value is None:
        msg = "Failed to evaluate captcha. Please reload the page and try again."
        raise ValueError(msg)

    return value


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


class PointPartType(StrEnum):
    MOLMO_2_INPUT_POINT = "molmo_2_input_point"


class PointPart(APIInterface):
    type: Literal[PointPartType.MOLMO_2_INPUT_POINT]
    x: int
    y: int
    time: float
    label: str = Field(default="object")


# Will be a union of different parts in the future
InputPart: TypeAlias = PointPart


class CreateMessageRequest(APIInterface):
    parent: str | None = Field(default=None)
    content: str = Field(min_length=1)
    input_parts: list[InputPart] = Field(default_factory=list)
    role: Role | None = Field(default=Role.User)
    original: str | None = Field(default=None)
    private: bool = Field(default=False)
    template: str | None = Field(default=None)
    model: str
    host: str | None = Field(default=None, deprecated=True)
    tool_call_id: str | None = Field(default=None)
    tool_definitions: Json[list[CreateToolDefinition]] | None = Field(default=None)
    selected_tools: list[str] | None = Field(default=None)
    enable_tool_calling: bool = Field(default=False)

    bypass_safety_check: bool = Field(default=False)

    captcha_token: Annotated[str | None, AfterValidator(captcha_token_required_if_captcha_enabled)] = Field(
        default=None
    )

    max_tokens: int | None = Field(default=None)
    temperature: float | None = Field(default=None)
    top_p: float | None = Field(default=None)
    stop: list[str] | None = Field(default_factory=list)  # type:ignore[arg-type] # https://github.com/pydantic/pydantic/issues/10950

    n: int | None = Field(
        default=1, ge=1, le=1
    )  # n has a max of 1 when streaming. if we allow for non-streaming requests we can go up to 50
    logprobs: int | None = Field(default=None, ge=0, le=10)  # logprobs has a max of 10

    extra_parameters: Json[dict[str, Any]] | None = Field(default=None)

    files: list[UploadedFile] | None = Field(default=None)

    @model_validator(mode="after")
    def check_original_and_parent_are_different(self) -> Self:
        if self.original is not None and self.parent == self.original:
            msg = "The original message cannot also be the parent"
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def check_assistant_message_has_a_parent(self) -> Self:
        if self.role is Role.Assistant and self.parent is None:
            msg = "Assistant messages must have a parent"
            raise ValueError(msg)

        return self

    @field_validator("content", mode="after")
    @classmethod
    def standardize_newlines(cls, value: str) -> str:
        return value.replace("\r\n", "\n")

    @field_validator("input_parts", mode="after")
    @classmethod
    def only_one_molmo_2_input_part_allowed(cls, value: list[InputPart]) -> list[InputPart]:
        molmo_2_point_parts = [part for part in value if part.type == PointPartType.MOLMO_2_INPUT_POINT]
        if len(molmo_2_point_parts) > 1:
            msg = "Only one Molmo 2 input part allowed per request"
            raise ValueError(msg)

        return value


class CreateMessageRequestWithFullMessages(BaseModel):
    parent_id: str | None = Field(default=None)
    parent: Message | None = Field(default=None)
    opts: InferenceOpts = Field(default_factory=InferenceOpts)
    max_steps: int | None = Field(default=None)
    extra_parameters: dict[str, Any] | None = Field(default=None)

    content: str = Field(min_length=1)
    role: Role
    original: str | None = Field(default=None)
    private: bool = Field(default=False)
    root: Message | None = Field(default=None)
    template: str | None = Field(default=None)
    model: str
    agent: str | None
    files: Sequence[UploadedFile] | None = Field(default=None)
    client: str
    captcha_token: str | None = Field()
    bypass_safety_check: bool = Field(default=False)

    tool_call_id: str | None = Field(default=None)
    create_tool_definitions: list[CreateToolDefinition] | None
    selected_tools: list[str] | None
    enable_tool_calling: bool

    mcp_server_ids: set[str] | None
    """Intended to be used by agent flows to pass MCP servers in"""

    @model_validator(mode="after")
    def parent_exists_if_parent_id_is_set(self) -> Self:
        if self.parent_id is not None and self.parent is None:
            msg = f"Parent message {self.parent_id} not found"
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def root_exists_when_root_id_is_defined_with_no_parent(self) -> Self:
        if self.parent is not None and self.root is None:
            msg = f"Message has an invalid root {self.parent.root}"
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def assistant_message_has_a_parent(self) -> Self:
        if self.role == Role.Assistant and self.parent is None:
            msg = "Assistant messages must have a parent"
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def original_message_and_parent_are_different(self) -> Self:
        if self.original is not None and self.parent_id is not None and self.original == self.parent_id:
            msg = "Original and parent messages must be different"
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def private_matches_root_private(self) -> Self:
        if self.root is not None and self.root.private != self.private:
            msg = "Visibility must be identical for all messages in a thread"
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def current_user_created_thread(self) -> Self:
        # Only the creator of a thread can create follow-up prompts
        if self.root is not None and self.root.creator != self.client:
            raise exceptions.Forbidden

        return self

    @model_validator(mode="after")
    def tool_response_creation_can_not_be_root(self) -> Self:
        if self.parent is None and self.role == Role.ToolResponse:
            msg = "Tool response must have parent"
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def tool_response_creation_must_have_tool_id(self) -> Self:
        if self.role == Role.ToolResponse and self.tool_call_id is None:
            msg = "Tool response must have tool call id"
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def parent_and_child_have_different_roles(self) -> Self:
        if self.parent is not None and self.parent.role != Role.ToolResponse and self.parent.role == self.role:
            msg = "Parent and child must have different roles"
            raise ValueError(msg)

        return self


# This is here because Pydantic complains about "Message" not being fully defined
CreateMessageRequestWithFullMessages.model_rebuild()
