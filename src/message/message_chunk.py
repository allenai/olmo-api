from typing import Any, Literal

from src import obj
from src.api_interface import APIInterface


class BaseChunk(APIInterface):
    message: obj.ID


class ModelResponseChunk(BaseChunk):
    content: str


class ToolCallChunk(BaseChunk):
    type: Literal["toolCall"]

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
    type: Literal["thinking"]

    content: str
    """The thinking content of the response."""

    id: str | None = None
    """The identifier of the thinking part."""
