from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator

from src import obj
from src.api_interface import APIInterface


class ChunkType(StrEnum):
    MODEL_RESPONSE = "modelResponse"
    TOOL_CALL = "toolCall"
    THINKING = "thinking"
    START = "start"
    END = "end"


class BaseChunk(APIInterface):
    message: obj.ID


class ModelResponseChunk(BaseChunk):
    type: Literal[ChunkType.MODEL_RESPONSE] = Field(init=False)
    content: str

    # HACK: This lets us make `type` required in the schema while also not requiring it in the init
    @field_validator("type", mode="before")
    @classmethod
    def add_type(cls, _v):
        cls.type = ChunkType.MODEL_RESPONSE


class ToolCallChunk(BaseChunk):
    type: Literal[ChunkType.TOOL_CALL] = Field(init=False)

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

    # HACK: This lets us make `type` required in the schema while also not requiring it in the init
    @field_validator("type", mode="before")
    @classmethod
    def add_type(cls, _v):
        cls.type = ChunkType.TOOL_CALL


class ThinkingChunk(BaseChunk):
    type: Literal[ChunkType.THINKING] = Field(init=False)

    content: str
    """The thinking content of the response."""

    id: str | None = None
    """The identifier of the thinking part."""

    # HACK: This lets us make `type` required in the schema while also not requiring it in the init
    @field_validator("type", mode="before")
    @classmethod
    def add_type(cls, _v):
        cls.type = ChunkType.THINKING


class StreamStartChunk(BaseChunk):
    type: Literal[ChunkType.START] = ChunkType.START


class StreamEndChunk(BaseChunk):
    type: Literal[ChunkType.END] = ChunkType.END


Chunk = ModelResponseChunk | ToolCallChunk | ThinkingChunk | StreamStartChunk | StreamEndChunk
