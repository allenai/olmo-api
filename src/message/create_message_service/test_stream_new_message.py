from pydantic_ai.messages import ModelResponse, TextPart, ThinkingPart, ToolCallPart, ToolCallPartDelta

from src.dao.engine_models.message import Message
from src.dao.engine_models.tool_definitions import ToolDefinition, ToolSource
from src.message.create_message_service.stream_new_message import map_response_to_final_output
from src.message.message_chunk import ErrorChunk, ErrorCode, ErrorSeverity
from src.pydantic_inference.pydantic_ai_helpers import pydantic_map_delta, pydantic_map_part


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
                description="desscription",
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
