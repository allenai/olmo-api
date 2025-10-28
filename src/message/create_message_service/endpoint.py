from dataclasses import dataclass, field
from enum import StrEnum
from time import time_ns
from typing import Any, cast

from flask import current_app
from flask import request as flask_request
from werkzeug import exceptions

import src.dao.message.message_models as message
from otel.default_tracer import get_default_tracer
from src import db
from src.auth.auth_service import authn
from src.config.get_config import cfg
from src.config.get_models import get_model_by_id
from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelConfig, PromptType
from src.dao.message.inference_opts_model import InferenceOpts
from src.dao.message.message_repository import BaseMessageRepository
from src.flask_pydantic_api.utils import UploadedFile
from src.message.create_message_request import (
    CreateMessageRequestWithFullMessages,
    CreateToolDefinition,
)
from src.message.create_message_service.safety import validate_message_security_and_safety
from src.message.create_message_service.stream_new_message import create_new_message
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.SafetyChecker import (
    SafetyCheckerType,
)
from src.message.validate_message_files_from_config import (
    validate_message_files_from_config,
)
from src.model_config.base_model_config import (
    validate_inference_parameters_against_model_constraints,
)

tracer = get_default_tracer()


class MessageType(StrEnum):
    MODEL = "model"
    AGENT = "agent"


@dataclass(kw_only=True)
class ModelMessageStreamInput:
    parent: str | None = None
    content: str
    role: message.Role | None = message.Role.User
    original: str | None = None
    private: bool = False
    template: str | None = None
    model: str

    tool_call_id: str | None = None
    tool_definitions: list[CreateToolDefinition] | None = None
    selected_tools: list[str] | None = None
    enable_tool_calling: bool = False

    mcp_server_ids: set[str] | None = None
    """Intended to be used by agent flows to pass MCP servers in"""

    bypass_safety_check: bool = False

    captcha_token: str | None = None

    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    stop: list[str] | None = field(default_factory=list)
    # n and logprobs are deliberately excluded since we don't currently support them

    extra_parameters: dict[str, Any] | None = None

    files: list[UploadedFile] | None = None

    request_type: MessageType


def get_inference_options(
    model: ModelConfig,
    parent_message: Message | None,
    max_tokens: int | None,
    temperature: float | None,
    top_p: float | None,
    stop: list[str] | None,
) -> message.InferenceOpts:
    # get the last inference options, either from the parent message or the model defaults if no parent
    default_inference_options = model.get_model_config_default_inference_options()
    parent_inference_options = message.InferenceOpts.from_message(parent_message)
    request_inference_options = message.InferenceOpts(
        max_tokens=max_tokens, temperature=temperature, top_p=top_p, stop=stop
    )

    merged_inference_options = (
        default_inference_options.model_dump()
        | (parent_inference_options.model_dump() if parent_inference_options is not None else {})
        | request_inference_options.model_dump()
    )

    return message.InferenceOpts.model_construct(**merged_inference_options)


@tracer.start_as_current_span("stream_message_from_model")
def stream_message_from_model(
    request: ModelMessageStreamInput,
    dbc: db.Client,
    storage_client: GoogleCloudStorage,
    message_repository: BaseMessageRepository,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
    # HACK: I'm getting agent support in quickly. Ideally we'd have a different, better way of handling requests for agents instead of models
    agent_id: str | None = None,
):
    client_agent = authn()
    model = get_model_by_id(request.model)
    parent_message, root_message, private = get_parent_and_root_messages_and_private(
        request.parent, message_repository, request.private, is_anonymous_user=client_agent.is_anonymous_user
    )

    inference_options = get_inference_options(
        model,
        parent_message=parent_message,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        stop=request.stop,
    )

    mapped_request = CreateMessageRequestWithFullMessages(
        parent_id=request.parent,
        parent=parent_message,
        opts=inference_options,
        extra_parameters=request.extra_parameters,
        content=request.content,
        role=cast(message.Role, request.role),
        original=request.original,
        private=private,
        root=root_message,
        template=request.template,
        model=request.model,
        agent=agent_id,
        client=client_agent.client,
        files=request.files,
        captcha_token=request.captcha_token,
        tool_call_id=request.tool_call_id,
        create_tool_definitions=request.tool_definitions,
        enable_tool_calling=request.enable_tool_calling,
        selected_tools=request.selected_tools,
        bypass_safety_check=request.bypass_safety_check,
        mcp_server_ids=request.mcp_server_ids,
    )

    if model.prompt_type == PromptType.FILES_ONLY and not cfg.feature_flags.allow_files_only_model_in_thread:
        current_app.logger.error("Tried to use a files only model in a normal thread stream %s/%s", id, model)

        # HACK: I want OLMoASR to be set up like a normal model but don't want people to stream to it yet
        model_not_available_message = "This model isn't available yet"
        raise exceptions.BadRequest(model_not_available_message)

    validate_message_files_from_config(request.files, config=model, has_parent=mapped_request.parent is not None)
    validate_inference_parameters_against_model_constraints(
        model,
        InferenceOpts(
            max_tokens=mapped_request.opts.max_tokens,
            temperature=mapped_request.opts.temperature,
            top_p=mapped_request.opts.top_p,
            stop=mapped_request.opts.stop,
            n=mapped_request.opts.n,
            logprobs=mapped_request.opts.logprobs,
        ),
    )

    user_ip_address = flask_request.remote_addr
    user_agent = flask_request.user_agent.string

    start_time_ns = time_ns()

    safety_check_elapsed_time, is_message_harmful = validate_message_security_and_safety(
        request=mapped_request,
        agent=client_agent,
        checker_type=checker_type,
        user_ip_address=user_ip_address,
        user_agent=user_agent,
    )

    return create_new_message(
        mapped_request,
        dbc,
        model=model,
        storage_client=storage_client,
        checker_type=checker_type,
        safety_check_elapsed_time=safety_check_elapsed_time,
        is_message_harmful=is_message_harmful,
        start_time_ns=start_time_ns,
        client_token=client_agent,
        message_repository=message_repository,
    )


def get_parent_and_root_messages_and_private(
    parent_message_id: str | None,
    message_repository: BaseMessageRepository,
    request_private: bool | None,
    is_anonymous_user: bool,
) -> tuple[Message | None, Message | None, bool]:
    parent_message = message_repository.get_message_by_id(parent_message_id) if parent_message_id is not None else None
    root_message = message_repository.get_message_by_id(parent_message.root) if parent_message is not None else None

    private = (
        # Anonymous users aren't allowed to share messages
        True
        if is_anonymous_user
        else (
            request_private
            if request_private is not None
            else root_message.private
            if root_message is not None
            else False
        )
    )

    return parent_message, root_message, private
