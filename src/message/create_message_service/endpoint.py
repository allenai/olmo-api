import json
from time import time_ns
from typing import cast

from flask import current_app
from flask import request as flask_request
from werkzeug import exceptions

import src.dao.message.message_models as message
from src import db, util
from src.auth.auth_service import authn
from src.config.get_config import cfg
from src.config.get_models import get_model_by_host_and_id
from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import PromptType
from src.dao.message.message_repository import BaseMessageRepository
from src.message.create_message_request import (
    CreateMessageRequest,
    CreateMessageRequestWithFullMessages,
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
from src.model_config.base_model_config import validate_inference_params


def format_message(obj) -> str:
    return json.dumps(obj=obj, cls=util.CustomEncoder) + "\n"


def create_message_v4(
    request: CreateMessageRequest,
    dbc: db.Client,
    storage_client: GoogleCloudStorage,
    message_repository: BaseMessageRepository,
    checker_type: SafetyCheckerType = SafetyCheckerType.GoogleLanguage,
):
    agent = authn()

    parent_message, root_message, private = get_parent_and_root_messages_and_private(
        request.parent, message_repository, request.private, is_anonymous_user=agent.is_anonymous_user
    )

    mapped_request = CreateMessageRequestWithFullMessages(
        parent_id=request.parent,
        parent=parent_message,
        opts=message.InferenceOpts(
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            n=request.n,
            top_p=request.top_p,
            logprobs=request.logprobs,
            stop=request.stop,
        ),
        extra_parameters=request.extra_parameters,
        content=request.content,
        role=cast(message.Role, request.role),
        original=request.original,
        private=private,
        root=root_message,
        template=request.template,
        model=request.model,
        host=request.host,
        client=agent.client,
        files=request.files,
        captcha_token=request.captcha_token,
        tool_call_id=request.tool_call_id,
        create_tool_definitions=request.tool_definitions,
        enable_tool_calling=request.enable_tool_calling,
        selected_tools=request.selected_tools,
        bypass_safety_check=request.bypass_safety_check,
    )

    model = get_model_by_host_and_id(mapped_request.host, mapped_request.model)
    if model.prompt_type == PromptType.FILES_ONLY and not cfg.feature_flags.allow_files_only_model_in_thread:
        current_app.logger.error("Tried to use a files only model in a normal thread stream %s/%s", id, model)

        # HACK: I want OLMoASR to be set up like a normal model but don't want people to stream to it yet
        model_not_available_message = "This model isn't available yet"
        raise exceptions.BadRequest(model_not_available_message)

    validate_message_files_from_config(request.files, config=model, has_parent=mapped_request.parent is not None)
    validate_inference_params(model)

    if model.top_p_default is not None:
        if model.top_p_lower is not None and model.top_p_default < model.top_p_lower:
            msg = "Default top_p must be greater than or equal to the lower limit"
            raise ValueError(msg)
        if model.top_p_upper is not None and model.top_p_default > model.top_p_upper:
            msg = "Default top_p must be less than or equal to the upper limit"
            raise ValueError(msg)

    user_ip_address = flask_request.remote_addr
    user_agent = flask_request.user_agent.string

    start_time_ns = time_ns()

    safety_check_elapsed_time, is_message_harmful = validate_message_security_and_safety(
        request=mapped_request,
        agent=agent,
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
        agent=agent,
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
