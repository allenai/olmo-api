from collections.abc import Sequence
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, Json, model_validator
from werkzeug import exceptions

from src.api_interface import APIInterface
from src.config.get_config import get_config
from src.dao.engine_models.message import Message
from src.dao.message.message_models import (
    InferenceOpts,
    Role,
    logprobs,
    max_tokens,
    num,
    temperature,
    top_p,
)
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


class CreateMessageRequest(APIInterface):
    # TODO: Validate that the parent role is different from this role and that it exists
    parent: str | None = Field(default=None)
    content: str = Field(min_length=1)
    role: Role | None = Field(default=Role.User)
    original: str | None = Field(default=None)
    private: bool = Field(default=False)
    template: str | None = Field(default=None)
    model: str
    host: str
    tool_call_id: str | None = Field(default=None)
    tool_definitions: Json[list[CreateToolDefinition]] | None = Field(default=None)
    selected_tools: list[str] | None = Field(default=None)
    enable_tool_calling: bool = Field(default=False)

    captcha_token: Annotated[str | None, AfterValidator(captcha_token_required_if_captcha_enabled)] = Field(
        default=None
    )

    max_tokens: int = Field(
        default=max_tokens.default,
        ge=max_tokens.min,
        le=max_tokens.max,
        multiple_of=max_tokens.step,
    )
    temperature: float = Field(
        default=temperature.default,
        ge=temperature.min,
        le=temperature.max,
        multiple_of=temperature.step,
    )
    n: int = Field(default=num.default, ge=num.min, le=num.max, multiple_of=num.step)
    top_p: float = Field(default=top_p.default, ge=top_p.min, le=top_p.max, multiple_of=top_p.step)
    logprobs: int | None = Field(
        default=logprobs.default,
        ge=logprobs.min,
        le=logprobs.max,
        multiple_of=logprobs.step,
    )
    stop: list[str] | None = Field(default_factory=list)  # type:ignore[arg-type] # https://github.com/pydantic/pydantic/issues/10950

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


class CreateMessageRequestWithFullMessages(BaseModel):
    parent_id: str | None = Field(default=None)
    parent: Message | None = Field(default=None)
    opts: InferenceOpts = Field(default_factory=InferenceOpts)
    content: str = Field(min_length=1)
    role: Role
    original: str | None = Field(default=None)
    private: bool = Field(default=False)
    root: Message | None = Field(default=None)
    template: str | None = Field(default=None)
    model: str
    host: str
    files: Sequence[UploadedFile] | None = Field(default=None)
    client: str
    captcha_token: str | None = Field()

    tool_call_id: str | None = Field(default=None)
    create_tool_definitions: list[CreateToolDefinition] | None
    selected_tools: list[str] | None
    enable_tool_calling: bool

    model_config = ConfigDict(validate_assignment=True)

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
