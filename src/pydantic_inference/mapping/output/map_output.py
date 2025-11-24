from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from pydantic_ai.messages import (
    FinalResultEvent,
    ModelResponsePart,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
)
from src.dao.engine_models.message import Message
from src.message.message_chunk import (
    Chunk,
    ErrorChunk,
    ErrorCode,
    ErrorSeverity,
    ModelResponseChunk,
    ThinkingChunk,
    ToolCallChunk,
)
from src.pydantic_inference.pydantic_ai_helpers import find_tool_def_by_name


def pydantic_map_chunk(chunk: PartStartEvent | PartDeltaEvent | FinalResultEvent, message: Message) -> Chunk | None:
    match chunk:
        case PartStartEvent():
            return _pydantic_map_part(chunk.part, message)
        case PartDeltaEvent():
            return _pydantic_map_delta(chunk.delta, message)
        case _:
            return None


def _pydantic_map_part(part: ModelResponsePart, message: Message) -> Chunk:
    match part:
        case TextPart():
            return ModelResponseChunk(
                message=message.id,
                content=part.content,
            )
        case ThinkingPart():
            return ThinkingChunk(
                message=message.id,
                content=part.content or "",
            )
        case ToolCallPart():
            try:
                tool_def = find_tool_def_by_name(message, part.tool_name)
            except RuntimeError as e:
                current_span = trace.get_current_span()
                current_span.set_status(Status(StatusCode.ERROR))
                current_span.record_exception(e)
                return ErrorChunk(
                    message=message.id,
                    error_code=ErrorCode.TOOL_CALL_ERROR,
                    error_description=str(e),
                    error_severity=ErrorSeverity.ERROR,
                )

            return ToolCallChunk(
                message=message.id,
                tool_call_id=part.tool_call_id,
                tool_name=part.tool_name,
                args=part.args,
                tool_source=tool_def.tool_source,
            )
        case _:
            msg = "unsupported response part"
            raise NotImplementedError(msg)


def _pydantic_map_delta(part: TextPartDelta | ToolCallPartDelta | ThinkingPartDelta, message: Message) -> Chunk:
    match part:
        case TextPartDelta():
            return ModelResponseChunk(message=message.id, content=part.content_delta or "")
        case ThinkingPartDelta():
            return ThinkingChunk(message=message.id, content=part.content_delta or "")
        case ToolCallPartDelta():
            try:
                tool_def = find_tool_def_by_name(message, part.tool_name_delta) if part.tool_name_delta else None
            except RuntimeError as e:
                current_span = trace.get_current_span()
                current_span.set_status(Status(StatusCode.ERROR))
                current_span.record_exception(e)
                return ErrorChunk(
                    message=message.id,
                    error_code=ErrorCode.TOOL_CALL_ERROR,
                    error_description=str(e),
                    error_severity=ErrorSeverity.ERROR,
                )

            return ToolCallChunk(
                message=message.id,
                tool_call_id=part.tool_call_id or "",
                tool_name=part.tool_name_delta or "",
                args=part.args_delta,
                tool_source=tool_def.tool_source if tool_def else None,
            )


__all__ = ["pydantic_map_chunk"]
