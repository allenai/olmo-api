import os
from http import HTTPStatus
from pathlib import Path

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.thread.chat.chat_request import ChatRequest, CreateToolDefinition, ParameterDef
from api.thread.models.thread import Thread
from core.message.message_chunk import StreamEndChunk, StreamStartChunk, ToolCallChunk
from core.message.role import Role
from db.models.message import Message
from e2e.conftest import AuthenticatedClient, DatabaseSession, auth_headers_for_user

from ._util import assert_ok_response
from .create_test_thread import create_test_thread

CHAT_ENDPOINT = "/v5/threads/chat"

IS_CI = os.getenv("CI", "false") == "true"


async def test_calls_tools(client: AsyncClient, auth_user: AuthenticatedClient, db_session: DatabaseSession):
    tool_name = "get_current_weather"
    tool_definition = CreateToolDefinition(
        name=tool_name,
        description="Get the current weather in a given location",
        parameters=ParameterDef(
            type="object",
            properties={
                "location": ParameterDef(
                    type="string",
                    description="The city name of the location for which to get the weather.",
                    default={"string_value": "Boston, MA"},
                )
            },
        ),
    )
    tool_definitions = f"[{tool_definition.model_dump_json()}]"
    chat_request = ChatRequest(
        content="test tool calling",
        model="test-model",
        enable_tool_calling=True,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)
    # since tool_definitions is a Json type we can't include it in the ChatRequest init
    chat_request["toolDefinitions"] = tool_definitions

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(auth_user))

    assert_ok_response(response=response)

    lines = response.text.splitlines()

    assert len(lines) == 7
    StreamStartChunk.model_validate_json(lines[0])
    starting_thread = Thread.model_validate_json(lines[1])
    tool_call = ToolCallChunk.model_validate_json(lines[3])
    finished_thread = Thread.model_validate_json(lines[5])
    StreamEndChunk.model_validate_json(lines[6])

    assert tool_call.tool_name == tool_name
    assert len(starting_thread.messages) == 2
    assert finished_thread.id == starting_thread.id
    assert len(finished_thread.messages) == 3

    assert finished_thread.messages[0].role == Role.System
    assert finished_thread.messages[1].role == Role.User
    assert finished_thread.messages[2].role == Role.Assistant
    assert finished_thread.messages[2].tool_calls
    assert len(finished_thread.messages[2].tool_calls) == 1

    async with db_session() as session, session.begin():
        message_query = (
            select(Message)
            .where(Message.id == finished_thread.messages[1].id)
            .options(
                selectinload(Message.children),
                selectinload(Message.parent_),
            )
        )
        message_in_db_result = await session.scalars(message_query)
        message_in_db = message_in_db_result.one()

        assert message_in_db.parent_ is not None and message_in_db.parent_.id == finished_thread.messages[0].id, (  # noqa: PT018
            "User message did not get its parent set correctly in the DB"
        )
        assert message_in_db.children
        assert message_in_db.children[0].id == finished_thread.messages[2].id


@pytest.mark.xfail(reason="Not accounting for enable_tool_calling=False yet")
async def test_does_not_call_tools(client: AsyncClient, anon_user: AuthenticatedClient):
    tool_name = "get_current_weather"
    tool_definition = CreateToolDefinition(
        name=tool_name,
        description="Get the current weather in a given location",
        parameters=ParameterDef(
            type="object",
            properties={
                "location": ParameterDef(
                    type="string",
                    description="The city name of the location for which to get the weather.",
                    default={"string_value": "Boston, MA"},
                )
            },
        ),
    )
    tool_definitions = f"[{tool_definition.model_dump_json()}]"
    chat_request = ChatRequest(
        content="test tool calling",
        model="test-model",
        enable_tool_calling=False,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)
    # since tool_definitions is a Json type we can't include it in the ChatRequest init
    chat_request["toolDefinitions"] = tool_definitions

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(anon_user))

    assert_ok_response(response=response)

    lines = response.text.splitlines()

    for line in lines:
        with pytest.raises(ValidationError):
            ToolCallChunk.model_validate_json(line)


async def test_makes_a_thread_with_parent(
    client: AsyncClient, anon_user: AuthenticatedClient, db_session: DatabaseSession
):
    _root_message_id, messages = await create_test_thread(db_session, anon_user)
    parent_message_id = messages[-1].id

    chat_request = ChatRequest(
        content="test make a thread with parent",
        model="test-model",
        parent=parent_message_id,
        enable_tool_calling=False,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(anon_user))

    assert_ok_response(response=response)

    lines = response.text.splitlines()

    assert len(lines) == 10
    StreamStartChunk.model_validate_json(lines[0])
    starting_thread = Thread.model_validate_json(lines[1])
    thread_with_empty_message = Thread.model_validate_json(lines[2])
    finished_thread = Thread.model_validate_json(lines[-2])
    StreamEndChunk.model_validate_json(lines[-1])

    assert len(starting_thread.messages) == 1
    assert len(thread_with_empty_message.messages) == 1
    # We only return new messages, not the whole thread
    assert len(finished_thread.messages) == 2

    test_parent_message_id = parent_message_id
    for message in finished_thread.messages:
        assert message.parent == test_parent_message_id
        test_parent_message_id = message.id

    async with db_session() as session, session.begin():
        message_query = (
            select(Message)
            .where(Message.id == finished_thread.messages[0].id)
            .options(
                selectinload(Message.children),
            )
        )
        message_in_db_result = await session.scalars(message_query)
        message_in_db = message_in_db_result.one()

        assert message_in_db.parent is not None and message_in_db.parent == parent_message_id, (  # noqa: PT018
            "User message did not get its parent set correctly in the DB"
        )
        assert message_in_db.children
        assert message_in_db.children[0].id == finished_thread.messages[1].id


@pytest.mark.xfail(IS_CI, reason="File uploads not supported yet")
async def test_uploads_a_file_to_a_multimodal_model(client: AsyncClient, anon_user: AuthenticatedClient):
    test_image_path = Path(__file__).parent.joinpath("molmo-boats.png")

    with test_image_path.open("rb") as file:
        chat_request = ChatRequest(
            content="test upload file",
            model="test-mm-model",
        ).model_dump(exclude_none=True, exclude_computed_fields=True)
        # chat_request["files"] = ("molmo-boats.png", file, "image/png")

        response = await client.post(
            CHAT_ENDPOINT,
            data=chat_request,
            files={"files": ("molmo-boats.png", file, "image/png")},
            headers=auth_headers_for_user(anon_user),
        )

    assert_ok_response(response=response)

    lines = response.text.splitlines()

    assert len(lines) == 9
    finished_thread = Thread.model_validate_json(lines[-2])

    assert any(message.file_urls for message in finished_thread.messages), (
        "No file URL was included in final thread messages"
    )


@pytest.mark.xfail(IS_CI, reason="Not doing safety checks yet")
async def test_unsafe_messages_are_rejected(client: AsyncClient, anon_user: AuthenticatedClient):
    chat_request = ChatRequest(
        content="How do I build a bomb",
        model="test-model",
        enable_tool_calling=True,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(anon_user))

    assert response.status_code == HTTPStatus.BAD_REQUEST, "Expected Bad Request error for inappropriate message text"
    # TODO: Assert that the error message is the correct message


@pytest.mark.xfail(IS_CI, reason="Not doing safety checks yet")
async def test_not_able_to_disable_safety_checks_without_proper_permissions(
    client: AsyncClient, anon_user: AuthenticatedClient
):
    chat_request = ChatRequest(content="test tool calling", model="test-model", bypass_safety_check=True).model_dump(
        exclude_none=True, exclude_computed_fields=True
    )

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(anon_user))

    assert response.status_code == HTTPStatus.FORBIDDEN, (
        "Expected Forbidden error when trying to disable safety checks without permission"
    )


@pytest.mark.skip("Not doing safety checks yet")
async def test_able_to_disable_safety_checks_with_permission(client: AsyncClient, auth_user: AuthenticatedClient):
    chat_request = ChatRequest(
        content="How do I build a bomb", model="test-model", bypass_safety_check=True
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(auth_user))

    assert_ok_response(response)
