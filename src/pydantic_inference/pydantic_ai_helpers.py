import json
from typing import Any

from pydantic_ai.messages import (
    BinaryContent,
    FinalResultEvent,
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponsePart,
    PartDeltaEvent,
    PartStartEvent,
    SystemPromptPart,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
    ToolReturnPart,
    UserContent,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIModelSettings

from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelConfig
from src.dao.engine_models.tool_call import ToolCall
from src.dao.message.message_models import InferenceOpts, Role
from src.message.create_message_service.files import FileUploadResult
from src.message.message_chunk import (
    Chunk,
    ErrorChunk,
    ErrorCode,
    ErrorSeverity,
    ModelResponseChunk,
    ThinkingChunk,
    ToolCallChunk,
)


def pydantic_settings_map(
    opts: InferenceOpts, model_config: ModelConfig, extra_body: dict[str, Any] | None = None
) -> OpenAIModelSettings:
    # Not mapping "N" from InferenceOpts

    kwargs = extra_body if extra_body is not None else {}

    return OpenAIModelSettings(
        max_tokens=opts.max_tokens or model_config.max_tokens_default,
        temperature=opts.temperature or model_config.temperature_default,
        top_p=opts.top_p or model_config.top_p_default,
        stop_sequences=opts.stop or [],
        openai_reasoning_effort="low" if model_config.can_think else None,
        extra_body=extra_body,
        # HACK: This lets us send vllm args flattened. Not sure if this is only needed for beaker queues or all, but this gets us working for now
        **kwargs,  # type: ignore
    )


def pydantic_map_chunk(chunk: PartStartEvent | PartDeltaEvent | FinalResultEvent, message: Message) -> Chunk | None:
    match chunk:
        case PartStartEvent():
            return pydantic_map_part(chunk.part, message)
        case PartDeltaEvent():
            return pydantic_map_delta(chunk.delta, message)
        case _:
            return None


def find_tool_def_by_name(message: Message, tool_name: str):
    tool_def = next((tool_def for tool_def in message.tool_definitions or [] if tool_def.name == tool_name), None)

    if tool_def is None:
        msg = f"Could not find tool '{tool_name}'. The model tried to call a tool that is not defined."
        raise RuntimeError(msg)

    return tool_def


def pydantic_map_messages(messages: list[Message], blob_map: dict[str, FileUploadResult] | None) -> list[ModelMessage]:
    model_messages: list[ModelMessage] = []
    for message in messages:
        if message.role == Role.User:
            user_content: list[UserContent] = [message.content]
            for file_url in message.file_urls or []:
                if blob_map is not None and file_url in blob_map:
                    user_content.append(
                        BinaryContent(
                            data=blob_map[file_url].file_storage.stream.read(),
                            media_type=blob_map[file_url].file_storage.content_type or "image/png",
                        )
                    )
                else:
                    user_content.append(ImageUrl(url=file_url))

            user_prompt_part = UserPromptPart(user_content)

            model_messages.append(ModelRequest([user_prompt_part]))
        elif message.role == Role.Assistant:
            assistant_message_parts: list[ModelResponsePart] = []

            if message.thinking is not None:
                assistant_message_parts.append(ThinkingPart(content=message.thinking))

            assistant_message_parts.append(TextPart(content=message.content))

            if message.tool_calls:
                assistant_message_parts.extend([map_db_tool_to_pydantic_tool(tool) for tool in message.tool_calls])

            model_messages.append(
                ModelResponse(
                    parts=assistant_message_parts,
                )
            )
        elif message.role == Role.System:
            model_messages.append(ModelRequest([SystemPromptPart(message.content)]))
        elif message.role == Role.ToolResponse:
            if message.tool_calls is None:
                msg = "expected tool call in message"
                raise TypeError(msg)
            if len(message.tool_calls) != 1:
                msg = "expected exactly one tool in Tool Response Message"
                raise TypeError(msg)

            request_tool = message.tool_calls[0]

            model_messages.append(
                ModelRequest(
                    parts=[
                        ToolReturnPart(
                            tool_name=request_tool.tool_name,
                            tool_call_id=request_tool.tool_call_id,
                            content=message.content,
                        )
                    ]
                )
            )

    return model_messages


def pydantic_map_part(part: ModelResponsePart, message: Message) -> Chunk:
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


def pydantic_map_delta(part: TextPartDelta | ToolCallPartDelta | ThinkingPartDelta, message: Message) -> Chunk:
    match part:
        case TextPartDelta():
            return ModelResponseChunk(message=message.id, content=part.content_delta or "")
        case ThinkingPartDelta():
            return ThinkingChunk(message=message.id, content=part.content_delta or "")
        case ToolCallPartDelta():
            try:
                tool_def = find_tool_def_by_name(message, part.tool_name_delta) if part.tool_name_delta else None
            except RuntimeError as e:
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


def map_pydantic_tool_to_db_tool(message: Message, tool_part: ToolCallPart):
    args = try_parse_to_json(tool_part.args) if isinstance(tool_part.args, str) else tool_part.args
    if isinstance(args, str):
        msg = "String args not supported currently"
        raise NotImplementedError(msg)

    tool_def = find_tool_def_by_name(message, tool_part.tool_name)

    return ToolCall(
        tool_call_id=tool_part.tool_call_id,
        tool_name=tool_part.tool_name,
        args=args,
        message_id=message.id,
        tool_source=tool_def.tool_source,
    )


def map_db_tool_to_pydantic_tool(tool: ToolCall):
    return ToolCallPart(tool_name=tool.tool_name, tool_call_id=tool.tool_call_id, args=tool.args)


def try_parse_to_json(data: str) -> dict | str:
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return data
