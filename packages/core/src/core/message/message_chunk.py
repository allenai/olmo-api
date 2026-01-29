from enum import StrEnum
from typing import Any, Literal

from pydantic import computed_field

import core.object_id as obj
from core.api_interface import APIInterface
from core.message.token_log_probs import TokenLogProbs
from core.tools.tool_source import ToolSource


class MessageChunk(APIInterface):
    message: obj.ID
    content: str
    logprobs: list[list[TokenLogProbs]] | None = None


class ChunkType(StrEnum):
    MODEL_RESPONSE = "modelResponse"
    TOOL_CALL = "toolCall"
    ERROR = "error"
    THINKING = "thinking"
    START = "start"
    END = "end"


class ErrorCode(StrEnum):
    TOOL_CALL_ERROR = "toolCallError"


class ErrorSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class MessageStreamError(APIInterface):
    message: obj.ID
    error: str
    reason: str


class BaseChunk(APIInterface):
    message: obj.ID


class ModelResponseChunk(BaseChunk):
    # HACK: This lets us make `type` required in the schema while also not requiring it in the init
    @computed_field  # type: ignore
    @property
    def type(self) -> Literal[ChunkType.MODEL_RESPONSE]:
        return ChunkType.MODEL_RESPONSE

    content: str


class ToolCallChunk(BaseChunk):
    # HACK: This lets us make `type` required in the schema while also not requiring it in the init
    @computed_field  # type: ignore
    @property
    def type(self) -> Literal[ChunkType.TOOL_CALL]:
        return ChunkType.TOOL_CALL

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

    tool_source: ToolSource | None


class ErrorChunk(BaseChunk):
    # HACK: This lets us make `type` required in the schema while also not requiring it in the init
    @computed_field  # type: ignore
    @property
    def type(self) -> Literal[ChunkType.ERROR]:
        return ChunkType.ERROR

    error_code: ErrorCode
    error_description: str
    error_severity: ErrorSeverity = ErrorSeverity.ERROR


class ThinkingChunk(BaseChunk):
    # HACK: This lets us make `type` required in the schema while also not requiring it in the init
    @computed_field  # type: ignore
    @property
    def type(self) -> Literal[ChunkType.THINKING]:
        return ChunkType.THINKING

    content: str
    """The thinking content of the response."""

    id: str | None = None
    """The identifier of the thinking part."""


class StreamStartChunk(BaseChunk):
    # HACK: This lets us make `type` required in the schema while also not requiring it in the init
    @computed_field  # type: ignore
    @property
    def type(self) -> Literal[ChunkType.START]:
        return ChunkType.START


class StreamEndChunk(BaseChunk):
    # HACK: This lets us make `type` required in the schema while also not requiring it in the init
    @computed_field  # type: ignore
    @property
    def type(self) -> Literal[ChunkType.END]:
        return ChunkType.END


Chunk = ModelResponseChunk | ToolCallChunk | ErrorChunk | ThinkingChunk | StreamStartChunk | StreamEndChunk
