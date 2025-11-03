import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ThinkingPart, ToolCallPart, ToolCallPartDelta
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from src import db
from src.auth.token import Token
from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelConfig, ModelHost, ModelType, PromptType
from src.dao.engine_models.tool_call import ToolCall
from src.dao.engine_models.tool_definitions import ToolDefinition, ToolSource
from src.dao.message.message_models import MessageStreamError, Role
from src.dao.message.message_repository import MessageRepository
from src.message.create_message_request import CreateMessageRequestWithFullMessages
from src.message.create_message_service.stream_new_message import map_response_to_final_output, stream_new_message
from src.message.message_chunk import ChunkType, ErrorChunk, ErrorCode, ErrorSeverity, StreamEndChunk, StreamStartChunk
from src.pydantic_inference.pydantic_ai_helpers import pydantic_map_delta, pydantic_map_part
from src.thread.thread_models import Thread


def test_map_final_output_should_map_when_there_is_an_empty_text_part_at_start():
    response = ModelResponse([TextPart("foo"), ThinkingPart("thinking"), TextPart("bar")])
    reply = Message(
        id="fake_message",
        content="content",
        creator="creator",
        role="Assistant",
        opts={},
        root="root",
        final=True,
        private=False,
        model_id="model_id",
        model_host="model_host",
        deleted=None,
        parent="parent",
        template=None,
        logprobs=None,
        completion=None,
        original=None,
        model_type="chat",
        finish_reason=None,
        harmful=False,
        expiration_time=None,
    )

    output = map_response_to_final_output(response, reply)

    assert output.text == "foo\n\nbar"
    assert output.thinking == "thinking"
    assert output.tool_parts == []


def test_map_final_output_should_map_tool_parts():
    response = ModelResponse([
        ThinkingPart("thinking"),
        TextPart("bar"),
        ToolCallPart(tool_name="tool", tool_call_id="tool_call_id"),
    ])
    reply = Message(
        id="fake_message",
        content="content",
        creator="creator",
        role="Assistant",
        opts={},
        root="root",
        final=True,
        private=False,
        model_id="model_id",
        model_host="model_host",
        deleted=None,
        parent="parent",
        template=None,
        logprobs=None,
        completion=None,
        original=None,
        model_type="chat",
        finish_reason=None,
        harmful=False,
        expiration_time=None,
        tool_definitions=[
            ToolDefinition(
                id="td_id",
                name="tool",
                description="description",
                parameters=None,
                tool_source=ToolSource.INTERNAL,
                mcp_server_id=None,
            )
        ],
    )

    output = map_response_to_final_output(response, reply)

    assert output.text == "bar"
    assert output.thinking == "thinking"
    assert len(output.tool_parts) == 1
    assert output.tool_parts[0].tool_name == "tool"


def test_pydantic_map_part_should_return_error_chunk_when_tool_not_found():
    """Test that ErrorChunk is created when a tool is not found in message tool_definitions."""
    tool_call_part = ToolCallPart(tool_name="unknown_tool", tool_call_id="test_call_id", args={"param": "value"})

    reply = Message(
        id="fake_message",
        content="content",
        creator="creator",
        role="Assistant",
        opts={},
        root="root",
        final=False,
        private=False,
        model_id="model_id",
        model_host="model_host",
        deleted=None,
        parent="parent",
        template=None,
        logprobs=None,
        completion=None,
        original=None,
        model_type="chat",
        finish_reason=None,
        harmful=False,
        expiration_time=None,
        tool_definitions=[
            ToolDefinition(
                id="td_id",
                name="existing_tool",
                description="description",
                parameters=None,
                tool_source=ToolSource.INTERNAL,
                mcp_server_id=None,
            )
        ],
    )

    chunk = pydantic_map_part(tool_call_part, reply)

    assert isinstance(chunk, ErrorChunk)
    assert chunk.error_code == ErrorCode.TOOL_CALL_ERROR
    assert "unknown_tool" in chunk.error_description or "Could not find tool" in chunk.error_description
    assert chunk.error_severity == ErrorSeverity.ERROR
    assert chunk.message == "fake_message"


def test_pydantic_map_delta_should_return_error_chunk_when_tool_not_found():
    """Test that ErrorChunk is created from delta when tool is not found."""
    tool_call_delta = ToolCallPartDelta(tool_name_delta="unknown_tool", tool_call_id="test_call_id", args_delta=None)

    reply = Message(
        id="fake_message",
        content="content",
        creator="creator",
        role="Assistant",
        opts={},
        root="root",
        final=False,
        private=False,
        model_id="model_id",
        model_host="model_host",
        deleted=None,
        parent="parent",
        template=None,
        logprobs=None,
        completion=None,
        original=None,
        model_type="chat",
        finish_reason=None,
        harmful=False,
        expiration_time=None,
        tool_definitions=[
            ToolDefinition(
                id="td_id",
                name="existing_tool",
                description="description",
                parameters=None,
                tool_source=ToolSource.INTERNAL,
                mcp_server_id=None,
            )
        ],
    )

    chunk = pydantic_map_delta(tool_call_delta, reply)

    assert isinstance(chunk, ErrorChunk)
    assert chunk.error_code == ErrorCode.TOOL_CALL_ERROR
    assert chunk.error_severity == ErrorSeverity.ERROR
    assert chunk.message == "fake_message"


@pytest.mark.usefixtures("flask_request_context")
def test_yields_error_when_exceeded_max_steps(sql_alchemy: Session, dbc: db.Client, mocker: MockerFixture):
    mocker.patch("src.tools.tools_service.call_internal_tool", return_value="return")

    request = CreateMessageRequestWithFullMessages(
        content="test",
        role=Role.User,
        model="test-model",
        client="test-client",
        enable_tool_calling=True,
        max_steps=1,
        agent=None,
        captcha_token=None,
        create_tool_definitions=None,
        selected_tools=None,
        mcp_server_ids=None,
    )

    model = ModelConfig(
        id="test-model",
        host=ModelHost.TestBackend,
        name="Test model",
        description="Test model",
        model_type=ModelType.Chat,
        model_id_on_host="test-backend",
        can_call_tools=True,
        internal=True,
        prompt_type=PromptType.TEXT_ONLY,
        temperature_default=0,
        temperature_lower=0,
        temperature_upper=1.0,
        temperature_step=0.1,
        top_p_default=0,
        top_p_lower=0,
        top_p_upper=0,
        top_p_step=0,
        max_tokens_default=2048,
        max_tokens_lower=0,
        max_tokens_step=1,
        max_tokens_upper=2048,
    )

    user_message = Message(
        id="fake_message",
        content="content",
        creator="creator",
        role=Role.User,
        opts={},
        root="fake_message",
        final=True,
        private=False,
        model_id="model_id",
        model_host="model_host",
        deleted=None,
        parent=None,
        template=None,
        logprobs=None,
        completion=None,
        original=None,
        model_type="chat",
        finish_reason=None,
        harmful=False,
        expiration_time=None,
        tool_calls=[
            ToolCall(
                id="test-tool-call-1-1",
                tool_call_id="test-tool-call-1-1",
                tool_name="test tool 1",
                tool_source=ToolSource.INTERNAL,
                args=None,
                message_id="fake_message",
            ),
            ToolCall(
                id="test-tool-call-2-1",
                tool_call_id="test-tool-call-2-1",
                tool_name="test tool 2",
                tool_source=ToolSource.INTERNAL,
                args=None,
                message_id="fake_message",
            ),
        ],
        tool_definitions=[
            ToolDefinition(
                id="test-tool-1",
                name="test tool 1",
                description="test tool 1",
                tool_source=ToolSource.INTERNAL,
                parameters=None,
            ),
            ToolDefinition(
                id="test-tool-2",
                name="test tool 2",
                description="test tool 2",
                tool_source=ToolSource.INTERNAL,
                parameters=None,
            ),
        ],
    )
    sql_alchemy.add(user_message)

    message_chain = [user_message]

    stream_generator = stream_new_message(
        request=request,
        dbc=dbc,
        model=model,
        safety_check_elapsed_time=0,
        start_time_ns=0,
        client_token=Token(client="test-client", is_anonymous_user=False, token="token"),
        message_repository=MessageRepository(sql_alchemy),
        message_chain=message_chain,
        created_message=user_message,
        max_steps=1,
    )

    results = list(stream_generator)

    assert len(results) == 7

    assert isinstance(results[0], StreamStartChunk)
    assert results[0].type == ChunkType.START

    assert isinstance(results[-2], MessageStreamError)
    assert results[-2].error == "Call exceeded the max tool call limit of 1."

    assert isinstance(results[-1], StreamEndChunk)
    assert results[-1].type == ChunkType.END


@pytest.mark.usefixtures("flask_request_context")
def test_stream_finishes_if_max_steps_not_exceeded(sql_alchemy: Session, dbc: db.Client, mocker: MockerFixture):
    mocker.patch("src.tools.tools_service.call_internal_tool", return_value="return")

    request = CreateMessageRequestWithFullMessages(
        content="test",
        role=Role.User,
        model="test-model",
        client="test-client",
        enable_tool_calling=True,
        max_steps=1,
        agent=None,
        captcha_token=None,
        create_tool_definitions=None,
        selected_tools=None,
        mcp_server_ids=None,
    )

    model = ModelConfig(
        id="test-model",
        host=ModelHost.TestBackend,
        name="Test model",
        description="Test model",
        model_type=ModelType.Chat,
        model_id_on_host="test-backend",
        can_call_tools=True,
        internal=True,
        prompt_type=PromptType.TEXT_ONLY,
        temperature_default=0,
        temperature_lower=0,
        temperature_upper=1.0,
        temperature_step=0.1,
        top_p_default=0,
        top_p_lower=0,
        top_p_upper=0,
        top_p_step=0,
        max_tokens_default=2048,
        max_tokens_lower=0,
        max_tokens_step=1,
        max_tokens_upper=2048,
    )

    user_message = Message(
        id="fake_message",
        content="content",
        creator="creator",
        role=Role.User,
        opts={},
        root="fake_message",
        final=True,
        private=False,
        model_id="model_id",
        model_host="model_host",
        deleted=None,
        parent=None,
        template=None,
        logprobs=None,
        completion=None,
        original=None,
        model_type="chat",
        finish_reason=None,
        harmful=False,
        expiration_time=None,
        tool_calls=[
            ToolCall(
                id="test-tool-call-1-1",
                tool_call_id="test-tool-call-1-1",
                tool_name="test tool 1",
                tool_source=ToolSource.INTERNAL,
                args=None,
                message_id="fake_message",
            ),
            ToolCall(
                id="test-tool-call-2-1",
                tool_call_id="test-tool-call-2-1",
                tool_name="test tool 2",
                tool_source=ToolSource.INTERNAL,
                args=None,
                message_id="fake_message",
            ),
        ],
        tool_definitions=[
            ToolDefinition(
                id="test-tool-1",
                name="test tool 1",
                description="test tool 1",
                tool_source=ToolSource.INTERNAL,
                parameters=None,
            ),
            ToolDefinition(
                id="test-tool-2",
                name="test tool 2",
                description="test tool 2",
                tool_source=ToolSource.INTERNAL,
                parameters=None,
            ),
        ],
    )
    sql_alchemy.add(user_message)

    message_chain = [user_message]

    stream_generator = stream_new_message(
        request=request,
        dbc=dbc,
        model=model,
        safety_check_elapsed_time=0,
        start_time_ns=0,
        client_token=Token(client="test-client", is_anonymous_user=False, token="token"),
        message_repository=MessageRepository(sql_alchemy),
        message_chain=message_chain,
        created_message=user_message,
        max_steps=2,
    )

    results = list(stream_generator)

    assert not any(isinstance(chunk, MessageStreamError) for chunk in results)

    assert isinstance(results[-2], Message)
    flat_final_message = Thread.from_message(results[-2])
    assert len([message for message in flat_final_message.messages if message.role is Role.ToolResponse]) == 2

    assert isinstance(results[-1], StreamEndChunk)
    assert results[-1].type == ChunkType.END
