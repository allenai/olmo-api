import json
from typing import Any

from pydantic_ai.messages import (
    ToolCallPart,
)
from pydantic_ai.models.openai import OpenAIChatModelSettings
from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelConfig
from src.dao.engine_models.tool_call import ToolCall
from src.dao.message.message_models import InferenceOpts


def pydantic_settings_map(
    opts: InferenceOpts, model_config: ModelConfig, extra_body: dict[str, Any] | None = None
) -> OpenAIChatModelSettings:
    # Not mapping "N" from InferenceOpts

    kwargs = extra_body if extra_body is not None else {}

    return OpenAIChatModelSettings(
        max_tokens=opts.max_tokens or model_config.max_tokens_default,
        temperature=opts.temperature or model_config.temperature_default,
        top_p=opts.top_p or model_config.top_p_default,
        stop_sequences=opts.stop or [],
        openai_reasoning_effort="low" if model_config.can_think else None,
        extra_body=extra_body,
        # HACK: This lets us send vllm args flattened. Not sure if this is only needed for beaker queues or all, but this gets us working for now
        **kwargs,  # type: ignore
    )


def find_tool_def_by_name(message: Message, tool_name: str):
    tool_def = next((tool_def for tool_def in message.tool_definitions or [] if tool_def.name == tool_name), None)

    if tool_def is None:
        msg = f"Could not find tool '{tool_name}'. The model tried to call a tool that is not defined."
        raise RuntimeError(msg)

    return tool_def


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
