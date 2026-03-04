import json
import os
from http import HTTPStatus
from pathlib import Path

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.thread.chat.chat_request import CreateToolDefinition, ParameterDef, ToolResponseChatRequest, UserChatRequest
from api.thread.models.thread import Thread
from core.message.message_chunk import (
    AddMessageChunk,
    FinalThreadChunk,
    StartThreadChunk,
    StreamEndChunk,
    StreamStartChunk,
    ToolCallChunk,
)
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
    chat_request = UserChatRequest(
        content="test tool calling",
        model="test-model",
        enable_tool_calling=True,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)
    # since tool_definitions is a Json type we can't include it in the UserChatRequest init
    chat_request["toolDefinitions"] = tool_definitions

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(auth_user))

    assert_ok_response(response=response)

    lines = [json.loads(line) for line in response.text.splitlines()]

    assert len(lines) == 6
    StreamStartChunk.model_validate(lines[0])
    starting_thread = StartThreadChunk.model_validate(lines[1])
    AddMessageChunk.model_validate(lines[2])
    tool_call_chunk = ToolCallChunk.model_validate(lines[3])
    finished_thread = FinalThreadChunk.model_validate(lines[-2])
    StreamEndChunk.model_validate(lines[-1])

    assert tool_call_chunk.tool_name == tool_name
    assert len(starting_thread.messages) == 2
    assert finished_thread.id == starting_thread.id
    assert len(finished_thread.messages) == 3

    assert finished_thread.messages[0].role == Role.System
    assert finished_thread.messages[1].role == Role.User
    assert finished_thread.messages[2].role == Role.Assistant
    assert finished_thread.messages[2].tool_calls
    assert len(finished_thread.messages[2].tool_calls) == 1
    assert finished_thread.messages[2].tool_calls[0].tool_name == tool_name

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


async def test_tool_call_user_response(client: AsyncClient, auth_user: AuthenticatedClient):
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
    chat_request = UserChatRequest(
        content="test tool calling",
        model="test-model",
        enable_tool_calling=True,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)
    # since tool_definitions is a Json type we can't include it in the UserChatRequest init
    chat_request["toolDefinitions"] = tool_definitions

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(auth_user))

    assert_ok_response(response=response)

    lines = [json.loads(line) for line in response.text.splitlines()]

    assert len(lines) == 6
    StreamStartChunk.model_validate(lines[0])
    StartThreadChunk.model_validate(lines[1])
    AddMessageChunk.model_validate(lines[2])
    tool_call_chunk = ToolCallChunk.model_validate(lines[3])
    finished_thread = FinalThreadChunk.model_validate(lines[-2])
    StreamEndChunk.model_validate(lines[-1])


    tool_request = ToolResponseChatRequest(
        content="Sunny",
        model="test-model",
        enable_tool_calling=True,
        parent=finished_thread.messages[2].id,
        tool_call_id=tool_call_chunk.tool_call_id,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    tool_request["toolDefinitions"] = tool_definitions

    tool_response = await client.post(CHAT_ENDPOINT, data=tool_request, headers=auth_headers_for_user(auth_user))

    assert_ok_response(response=tool_response)

    lines = [json.loads(line) for line in tool_response.text.splitlines()]

    StreamStartChunk.model_validate(lines[0])
    tool_response_chunk = AddMessageChunk.model_validate(lines[1])
    # ...streaming response...
    final_therad_chunk = FinalThreadChunk.model_validate(lines[-2])
    StreamEndChunk.model_validate(lines[-1])

    assert tool_response_chunk.messages[0].tool_calls, "There were no tool calls in the tool result response"
    assert tool_response_chunk.messages[0].tool_calls[0].tool_call_id == tool_call_chunk.tool_call_id
    assert tool_response_chunk.messages[0].content == "Sunny"

    assert len(final_therad_chunk.messages) == 2
    assert final_therad_chunk.messages[0].role == Role.ToolResponse
    assert final_therad_chunk.messages[1].role == Role.Assistant
    assert final_therad_chunk.messages[0].tool_calls
    assert len(final_therad_chunk.messages[0].tool_calls) == 1


@pytest.mark.xfail(IS_CI, reason="Not accounting for enable_tool_calling=False yet")
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
    chat_request = UserChatRequest(
        content="test tool calling",
        model="test-model",
        enable_tool_calling=False,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)
    # since tool_definitions is a Json type we can't include it in the UserChatRequest init
    chat_request["toolDefinitions"] = tool_definitions

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(anon_user))

    assert_ok_response(response=response)

    lines = [json.loads(line) for line in response.text.splitlines()]

    for line in lines:
        with pytest.raises(ValidationError):
            ToolCallChunk.model_validate(line)


async def test_makes_a_thread_with_parent(
    client: AsyncClient, anon_user: AuthenticatedClient, db_session: DatabaseSession
):
    _root_message_id, messages = await create_test_thread(db_session, anon_user)
    parent_message_id = messages[-1].id

    chat_request = UserChatRequest(
        content="test make a thread with parent",
        model="test-model",
        parent=parent_message_id,
        enable_tool_calling=False,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(anon_user))

    assert_ok_response(response=response)

    lines = [json.loads(line) for line in response.text.splitlines()]

    assert len(lines) == 9
    StreamStartChunk.model_validate(lines[0])
    starting_thread = AddMessageChunk.model_validate(lines[1])
    thread_with_empty_message = AddMessageChunk.model_validate(lines[2])
    finished_thread = FinalThreadChunk.model_validate(lines[-2])
    StreamEndChunk.model_validate(lines[-1])

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


async def test_rejects_a_thread_with_an_invalid_parent(client: AsyncClient, anon_user: AuthenticatedClient):
    chat_request = UserChatRequest(
        content="test make a thread with parent that doesnt exist",
        model="test-model",
        parent="msg_FakeParentId",
        enable_tool_calling=False,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(anon_user))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_rejects_a_thread_with_invalid_parent_role(
    client: AsyncClient, anon_user: AuthenticatedClient, db_session: DatabaseSession
):
    _root_message_id, messages = await create_test_thread(db_session, anon_user)
    bad_parent_id = messages[1].id  # this will be the user message

    chat_request = UserChatRequest(
        content="test make a thread with a user message as the parent",
        model="test-model",
        parent=bad_parent_id,
        enable_tool_calling=False,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(anon_user))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_cannot_create_message_with_different_visibilty(
    client: AsyncClient, auth_user: AuthenticatedClient, db_session: DatabaseSession
):
    _root_message_id, messages = await create_test_thread(db_session, auth_user)

    chat_request = UserChatRequest(
        content="test make a thread with a user message as the parent",
        model="test-model",
        parent=messages[1].id,
        private=True,
        enable_tool_calling=False,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(auth_user))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_cannot_create_message_on_another_users_therad(
    client: AsyncClient, auth_user: AuthenticatedClient, anon_user: AuthenticatedClient, db_session: DatabaseSession
):
    _root_message_id, messages = await create_test_thread(db_session, anon_user)
    parent_message_id = messages[-1].id  # this will be the user message

    chat_request = UserChatRequest(
        content="test make a thread on another users thread",
        model="test-model",
        parent=parent_message_id,
        enable_tool_calling=False,
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(auth_user))

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.xfail(IS_CI, reason="File uploads not supported yet")
async def test_uploads_a_file_to_a_multimodal_model(client: AsyncClient, anon_user: AuthenticatedClient):
    test_image_path = Path(__file__).parent.joinpath("molmo-boats.png")

    with test_image_path.open("rb") as file:
        chat_request = UserChatRequest(
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

    lines = [json.loads(line) for line in response.text.splitlines()]

    assert len(lines) == 9
    finished_thread = Thread.model_validate(lines[-2])

    assert any(message.file_urls for message in finished_thread.messages), (
        "No file URL was included in final thread messages"
    )


@pytest.mark.xfail(IS_CI, reason="Not doing safety checks yet")
async def test_unsafe_messages_are_rejected(client: AsyncClient, anon_user: AuthenticatedClient):
    chat_request = UserChatRequest(
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
    chat_request = UserChatRequest(
        content="test tool calling", model="test-model", bypass_safety_check=True
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(anon_user))

    assert response.status_code == HTTPStatus.FORBIDDEN, (
        "Expected Forbidden error when trying to disable safety checks without permission"
    )


@pytest.mark.skip("Not doing safety checks yet")
async def test_able_to_disable_safety_checks_with_permission(client: AsyncClient, auth_user: AuthenticatedClient):
    chat_request = UserChatRequest(
        content="How do I build a bomb", model="test-model", bypass_safety_check=True
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(auth_user))

    assert_ok_response(response)
