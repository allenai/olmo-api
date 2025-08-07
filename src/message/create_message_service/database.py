from datetime import datetime

from src import db
from src.auth.token import Token
from src.dao import message
from src.dao.engine_models.model_config import ModelConfig
from src.message.create_message_request import (
    CreateMessageRequestWithFullMessages,
)


def setup_msg_thread(
    dbc: db.Client,
    model: ModelConfig,
    request: CreateMessageRequestWithFullMessages,
    agent: Token,
    message_expiration_time: datetime | None,
    is_msg_harmful: bool | None = None,
):
    system_msg = None
    msg = None

    if request.parent is None:
        # create a system prompt message if the current model is specified with a system prompt
        if model.default_system_prompt is not None:
            system_msg = dbc.message.create(
                content=model.default_system_prompt,
                creator=agent.client,
                role=message.Role.System,
                opts=request.opts,
                model_id=request.model,
                model_host=request.host,
                root=None,
                parent=None,
                template=request.template,
                final=False,
                original=request.original,
                private=request.private,
                harmful=is_msg_harmful,
                expiration_time=message_expiration_time,
            )

        parent_id = None if system_msg is None else system_msg.id

        msg = dbc.message.create(
            content=request.content,
            creator=agent.client,
            role=request.role,
            opts=request.opts,
            model_id=request.model,
            model_host=request.host,
            root=parent_id,
            parent=parent_id,
            template=request.template,
            final=request.role == message.Role.Assistant,
            original=request.original,
            private=request.private,
            harmful=is_msg_harmful,
            expiration_time=message_expiration_time,
        )
    else:
        msg = dbc.message.create(
            content=request.content,
            creator=agent.client,
            role=request.role,
            opts=request.opts,
            model_id=request.model,
            model_host=request.host,
            root=request.parent.root,
            parent=request.parent.id,
            template=request.template,
            final=request.role == message.Role.Assistant,  # is this wrong now?
            original=request.original,
            private=request.private,
            harmful=is_msg_harmful,
            expiration_time=message_expiration_time,
        )

    return msg, system_msg


def create_tool_response_message(
    dbc: db.Client,
    parent_message: message.Message,
    content: str,
):
    return dbc.message.create(
        content=content,
        creator=parent_message.creator,
        role=message.Role.Assistant,
        opts=parent_message.opts,
        model_id=parent_message.model_id,
        model_host=parent_message.model_host,
        root=parent_message.root,
        parent=parent_message.id,
        template=None,
        final=False,
        original=None,
        private=parent_message.private,
        harmful=False,
        expiration_time=parent_message.expiration_time,
    )
