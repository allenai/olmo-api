# Only allow new messages, editing can come with PUT

# Get model from DB
# Validate request against model config
# Get parent/root messages
# If some options aren't set, merge them with parent's options
# Reject requests to OlmoASR
# Safety check
# Upload files
# Save initial messages/thread to DB
# If it's a tool response, go down a different path
# Stream message

from collections.abc import Sequence
from typing import Annotated, Any, Self

from fastapi import Depends, UploadFile
from opentelemetry import trace
from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import GEN_AI_REQUEST_MODEL
from pydantic import (
    BaseModel,
    Field,
    model_validator,
)
from werkzeug import exceptions

from api.async_message_repository.async_message_repository import AsyncMessageRepositoryDependency
from api.logging.fastapi_logger import FastAPIStructLogger
from core.api_interface import APIInterface
from core.auth.token import Token
from core.message.role import Role
from db.models.inference_opts import InferenceOpts
from db.models.input_parts import InputPart
from db.models.message import Message

# We import PromptTemplate and ToolDefinition so Pydantic knows how to resolve them, preventing some model definition errors
from db.models.prompt_template import PromptTemplate  # noqa: F401
from db.models.tool_definitions import ToolDefinition  # noqa: F401


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


class CreateMessageRequestWithFullMessages(BaseModel):
    parent_id: str | None = Field(default=None)
    parent: Message | None = Field(default=None)
    opts: InferenceOpts = Field(default_factory=InferenceOpts)
    max_steps: int | None = Field(default=None)
    extra_parameters: dict[str, Any] | None = Field(default=None)

    content: str
    input_parts: list[InputPart] | None = Field(default=None)

    role: Role
    original: str | None = Field(default=None)
    private: bool = Field(default=False)
    root: Message | None = Field(default=None)
    template: str | None = Field(default=None)
    model: str
    agent: str | None
    files: Sequence[UploadFile] | None = Field(default=None)
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


logger = FastAPIStructLogger()


class ChatService:
    def __init__(self, message_repository: AsyncMessageRepositoryDependency):
        self.message_repository = message_repository

    async def stream_chat_message(self, request: CreateMessageRequestWithFullMessages, user: Token):
        logger.bind(model=request.model, user=user.client)
        trace.get_current_span().set_attributes({GEN_AI_REQUEST_MODEL: request.model, "user": user.client})


ChatServiceDependency = Annotated[ChatService, Depends()]
