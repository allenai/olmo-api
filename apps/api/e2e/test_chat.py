from httpx import AsyncClient

from api.thread.chat.chat_request import ChatRequest, CreateToolDefinition, ParameterDef
from api.thread.models.thread import Thread
from core.message.message_chunk import StreamEndChunk, StreamStartChunk, ToolCallChunk
from core.message.role import Role
from e2e.conftest import AuthenticatedClient, auth_headers_for_user

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


async def test_calls_a_tool(client: AsyncClient, auth_user: AuthenticatedClient):
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
    ).model_dump(exclude_none=True)
    # since tool_definitions is a Json type we can't include it in the ChatRequest init
    chat_request["toolDefinitions"] = tool_definitions

    response = await client.post(CHAT_ENDPOINT, data=chat_request, headers=auth_headers_for_user(auth_user))

    assert response.status_code == 200, (
        f"{response.url} responded with an non-success for an anonymous user: {response.text}"
    )

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
