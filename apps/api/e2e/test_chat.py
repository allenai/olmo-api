from pathlib import Path

import pytest
from apps.api.e2e._util import assert_ok_response
from apps.api.e2e.create_test_thread import create_test_thread
from httpx import AsyncClient
from pydantic import ValidationError

from api.thread.chat.chat_request import ChatRequest, CreateToolDefinition, ParameterDef
from api.thread.models.thread import Thread
from core.message.message_chunk import StreamEndChunk, StreamStartChunk, ToolCallChunk
from core.message.role import Role
from e2e.conftest import AuthenticatedClient, DatabaseSession, auth_headers_for_user

default_model_options = {
    "host": (None, "test_backend"),
    "model": (None, "test-model-no-tools"),
}

tool_call_model_options = {
    "host": (None, "test_backend"),
    "model": (None, "test-model"),
    "enableToolCalling": (None, "true"),
}

CHAT_ENDPOINT = "/v5/threads/chat"


async def test_calls_tools(client: AsyncClient, auth_user: AuthenticatedClient):
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

    assert len(lines) == 5
    StreamStartChunk.model_validate_json(lines[0])
    starting_thread = Thread.model_validate_json(lines[1])
    tool_call = ToolCallChunk.model_validate_json(lines[2])
    finished_thread = Thread.model_validate_json(lines[3])
    StreamEndChunk.model_validate_json(lines[4])

    assert tool_call.tool_name == tool_name
    assert len(starting_thread.messages) == 2
    assert finished_thread.id == starting_thread.id
    assert len(finished_thread.messages) == 3

    assert finished_thread.messages[0].role == Role.System
    assert finished_thread.messages[1].role == Role.User
    assert finished_thread.messages[2].role == Role.Assistant
    assert finished_thread.messages[2].tool_calls
    assert len(finished_thread.messages[2].tool_calls) == 1


@pytest.mark.skip("Not accounting for enable_tool_calling=False yet")
async def test_does_not_call_tools(client: AsyncClient, auth_user: AuthenticatedClient):
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

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(auth_user))

    assert_ok_response(response=response)

    lines = response.text.splitlines()

    for line in lines:
        with pytest.raises(ValidationError):
            ToolCallChunk.model_validate_json(line)


@pytest.mark.skip("Having async loading issues when getting the parent and root, will refactor!")
async def test_makes_a_thread_with_parent(
    client: AsyncClient, auth_user: AuthenticatedClient, db_session: DatabaseSession
):
    _root_message_id, messages = await create_test_thread(db_session, auth_user)
    parent_message_id = messages[-1].id

    chat_request = ChatRequest(
        content="test make a thread with parent", model="test-model", parent=parent_message_id
    ).model_dump(exclude_none=True, exclude_computed_fields=True)

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(auth_user))

    assert_ok_response(response=response)

    lines = response.text.splitlines()

    assert len(lines) == 5
    # StreamStartChunk.model_validate_json(lines[0])
    # starting_thread = Thread.model_validate_json(lines[1])
    # tool_call = ToolCallChunk.model_validate_json(lines[2])
    # finished_thread = Thread.model_validate_json(lines[3])
    # StreamEndChunk.model_validate_json(lines[4])


@pytest.mark.skip("File uploads not supported yet")
async def test_uploads_a_file_to_a_multimodal_model(client: AsyncClient, auth_user: AuthenticatedClient):
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
            headers=auth_headers_for_user(auth_user),
        )

    assert_ok_response(response=response)

    lines = response.text.splitlines()

    assert len(lines) == 9
    finished_thread = Thread.model_validate_json(lines[-2])

    assert any(message.file_urls for message in finished_thread.messages), (
        "No file URL was included in final thread messages"
    )
