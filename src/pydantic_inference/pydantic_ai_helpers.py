from pydantic_ai.messages import (
    BinaryContent,
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
from src.message.message_chunk import Chunk, ModelResponseChunk, ThinkingChunk, ToolCallChunk


def pydantic_settings_map(ops: InferenceOpts, model_config: ModelConfig) -> OpenAIModelSettings:
    # Not mapping "N" from InferenceOpts

    return OpenAIModelSettings(
        max_tokens=ops.max_tokens,
        temperature=ops.temperature,
        top_p=ops.top_p,
        stop_sequences=ops.stop or [],
        openai_reasoning_effort="low" if model_config.can_think else None,
    )


def pydantic_map_chunk(chunk: PartStartEvent | PartDeltaEvent, message: Message) -> Chunk:
    match chunk:
        case PartStartEvent():
            return pydantic_map_part(chunk.part, message)
        case PartDeltaEvent():
            return pydantic_map_delta(chunk.delta, message)


def find_tool_def_by_name(message: Message, tool_name: str):
    tool_def = next((tool_def for tool_def in message.tool_definitions or [] if tool_def.name == tool_name), None)

    if tool_def is None:
        msg = f"Could not find tool '{tool_name}' in message"
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
            tool_def = find_tool_def_by_name(message, part.tool_name)

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
            tool_def = find_tool_def_by_name(message, part.tool_name_delta) if part.tool_name_delta else None

            if tool_def is None:
                msg = "Missing tool name in tool call delta"
                raise RuntimeError(msg)

            return ToolCallChunk(
                message=message.id,
                tool_call_id=part.tool_call_id or "",
                tool_name=part.tool_name_delta or "",
                args=part.args_delta,
                tool_source=tool_def.tool_source,
            )


def map_pydantic_tool_to_db_tool(message: Message, tool_part: ToolCallPart):
    if isinstance(tool_part.args, str):
        msg = "String args not supported currently"
        raise NotImplementedError(msg)

    tool_def = find_tool_def_by_name(message, tool_part.tool_name)

    return ToolCall(
        tool_call_id=tool_part.tool_call_id,
        tool_name=tool_part.tool_name,
        args=tool_part.args,
        message_id=message.id,
        tool_source=tool_def.tool_source,
    )


def map_db_tool_to_pydantic_tool(tool: ToolCall):
    return ToolCallPart(tool_name=tool.tool_name, tool_call_id=tool.tool_call_id, args=tool.args)
