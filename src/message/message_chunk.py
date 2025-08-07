from enum import StrEnum
from typing import Any, Literal

from src import obj
from src.api_interface import APIInterface


class ChunkType(StrEnum):
    MODEL_RESPONSE = "modelResponse"
    TOOL_CALL = "toolCall"
    THINKING = "thinking"


class BaseChunk(APIInterface):
    message: obj.ID


class ModelResponseChunk(BaseChunk):
    type: Literal[ChunkType.MODEL_RESPONSE] = ChunkType.MODEL_RESPONSE
    content: str


class ToolCallChunk(BaseChunk):
    type: Literal[ChunkType.TOOL_CALL] = ChunkType.TOOL_CALL

    tool_call_id: str
    """The tool call identifier, this is used by some models including OpenAI.

    In case the tool call id is not provided by the model, Pydantic AI will generate a random one.
    """

    tool_name: str
    """The name of the tool to call."""

    args: str | dict[str, Any] | None = None
    """The arguments to pass to the tool.

    This is stored either as a JSON string or a Python dictionary depending on how data was received.
    """


class ThinkingChunk(BaseChunk):
    type: Literal[ChunkType.THINKING] = ChunkType.THINKING

    content: str
    """The thinking content of the response."""

    id: str | None = None
    """The identifier of the thinking part."""


Chunk = ModelResponseChunk | ToolCallChunk | ThinkingChunk
