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
) -> list[message.Message]:
    system_msg = None
    message_chain = []

    if request.parent is None and model.default_system_prompt is not None:
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
            final=True,
            original=request.original,
            private=request.private,
            harmful=is_msg_harmful,
            expiration_time=message_expiration_time,
        )

    if request.parent:
        message_chain.append(request.parent)

    if request.root is not None:
        msgs = message.Message.group_by_id(request.root.flatten())  # TODO fix loading of thread...
        while message_chain[-1].parent is not None:
            message_chain.append(msgs[message_chain[-1].parent])

    if system_msg is not None:
        message_chain.append(system_msg)

    message_chain.reverse()

    return message_chain


def create_user_message(
    dbc: db.Client,
    request: CreateMessageRequestWithFullMessages,
    parent: message.Message | None,
    agent: Token,
    message_expiration_time: datetime | None,
    is_msg_harmful: bool | None = None,
):
    return dbc.message.create(
        content=request.content,
        creator=agent.client,
        role=request.role,
        opts=request.opts,
        model_id=request.model,
        model_host=request.host,
        root=parent.root if parent is not None else None,
        parent=parent.id if parent is not None else None,
        template=request.template,
        final=True,
        original=request.original,
        private=request.private,
        harmful=is_msg_harmful,
        expiration_time=message_expiration_time,
    )


def create_tool_response_message(
    dbc: db.Client,
    parent_message: message.Message,
    content: str,
):
    return dbc.message.create(
        content=content,
        creator=parent_message.creator,
        role=message.Role.Enviroment,
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
