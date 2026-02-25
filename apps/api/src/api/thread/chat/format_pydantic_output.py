from collections.abc import Sequence
from typing import assert_never

from pydantic_ai import (
    AgentStreamEvent,
    BuiltinToolCallPart,
    ToolCallPart,
)
from pydantic_ai.messages import (
    ModelResponsePart,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
    ToolCallPartDelta,
)

from api.thread.models.flat_message import FlatMessage
from core.message.message_chunk import (
    Chunk,
    ModelResponseChunk,
    ThinkingChunk,
    ToolCallChunk,
)
from core.tools.tool_source import ToolSource
from db.models.message import Message


def find_tool_def_by_name(message: Message, tool_name: str):
    tool_def = next(
        (tool_def for tool_def in message.tool_definitions or [] if tool_def.name == tool_name),
        None,
    )

    if tool_def is None:
        msg = f"Could not find tool '{tool_name}'. The model tried to call a tool that is not defined."
        raise RuntimeError(msg)

    return tool_def


def map_pydantic_chunk(
    chunk: AgentStreamEvent, message_id: str, user_defined_tool_names: Sequence[str], mcp_tool_names: Sequence[str]
) -> Chunk | FlatMessage | None:
    match chunk:
        case PartStartEvent():
            return _pydantic_map_part(
                chunk.part, message_id, user_defined_tool_names=user_defined_tool_names, mcp_tool_names=mcp_tool_names
            )
        case PartDeltaEvent():
            return _pydantic_map_delta(chunk.delta, message_id)
        case _:
            return None


def _pydantic_map_part(
    part: ModelResponsePart, message_id: str, user_defined_tool_names: Sequence[str], mcp_tool_names: Sequence[str]
) -> Chunk:
    match part:
        case TextPart():
            return ModelResponseChunk(
                message=message_id,
                content=part.content,
            )
        case ThinkingPart():
            return ThinkingChunk(
                message=message_id,
                content=part.content or "",
            )
        case ToolCallPart() | BuiltinToolCallPart():
            is_user_tool = part.tool_name in user_defined_tool_names
            is_mcp_tool = not is_user_tool and part.tool_name in mcp_tool_names

            tool_source = (
                ToolSource.USER_DEFINED if is_user_tool else ToolSource.MCP if is_mcp_tool else ToolSource.INTERNAL
            )

            return ToolCallChunk(
                message=message_id,
                tool_call_id=part.tool_call_id,
                tool_name=part.tool_name,
                args=part.args,
                tool_source=tool_source,
            )
        case _:
            # assert_never(part)
            msg = "unsupported response part"
            raise NotImplementedError(msg)


def _pydantic_map_delta(part: TextPartDelta | ToolCallPartDelta | ThinkingPartDelta, message_id: str) -> Chunk:
    match part:
        case TextPartDelta():
            return ModelResponseChunk(message=message_id, content=part.content_delta or "")
        case ThinkingPartDelta():
            return ThinkingChunk(message=message_id, content=part.content_delta or "")
        case ToolCallPartDelta():
            # try:
            #     tool_def = find_tool_def_by_name(message_id, part.tool_name_delta) if part.tool_name_delta else None
            # except RuntimeError as e:
            #     current_span = trace.get_current_span()
            #     current_span.set_status(Status(StatusCode.ERROR))
            #     current_span.record_exception(e)
            #     return ErrorChunk(
            #         message=message_id,
            #         error_code=ErrorCode.TOOL_CALL_ERROR,
            #         error_description=str(e),
            #         error_severity=ErrorSeverity.ERROR,
            #     )

            return ToolCallChunk(
                message=message_id,
                tool_call_id=part.tool_call_id or "",
                tool_name=part.tool_name_delta or "",
                args=part.args_delta,
                tool_source=None,
                # tool_source=tool_def.tool_source if tool_def else None,
            )
        case _:
            assert_never(part)
            msg = "unsupported response part"
            raise NotImplementedError(msg)


__all__ = ["map_pydantic_chunk"]
