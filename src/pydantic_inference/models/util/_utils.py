import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

if TYPE_CHECKING:
    from pydantic_ai import messages as _messages

_datetime_ta = TypeAdapter(datetime)


def generate_tool_call_id() -> str:
    """Generate a tool call id.

    Ensure that the tool call id is unique.
    """
    return f"pyd_ai_{uuid.uuid4().hex}"


def number_to_datetime(x: float) -> datetime:
    return _datetime_ta.validate_python(x)


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def guard_tool_call_id(
    t: _messages.ToolCallPart
    | _messages.ToolReturnPart
    | _messages.RetryPromptPart
    | _messages.BuiltinToolCallPart
    | _messages.BuiltinToolReturnPart,
) -> str:
    """Type guard that either returns the tool call id or generates a new one if it's None."""
    return t.tool_call_id or generate_tool_call_id()
