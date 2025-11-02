"""
Custom Pydantic Fields
-----------------------

Reusable Pydantic field types for common patterns like JSON string parsing.
"""
from typing import Annotated, Any

from pydantic import BeforeValidator, Field


def parse_json_string(value: str | list | dict | None) -> list | dict | None:
    """
    Parse JSON string to Python object.

    Handles cases where value is already parsed (dict/list) or is a JSON string.
    Returns None for None or empty string.
    """
    if value is None or value == "":
        return None

    if isinstance(value, (dict, list)):
        # Already parsed (happens in tests or when using JSON body)
        return value

    if isinstance(value, str):
        import json
        return json.loads(value)

    raise ValueError(f"Expected JSON string, dict, or list, got {type(value)}")


# Type alias for JSON string fields
JsonString = Annotated[
    list | dict | None,
    BeforeValidator(parse_json_string),
    Field(default=None)
]

# Specific types for common patterns
JsonList = Annotated[list | None, BeforeValidator(parse_json_string)]
JsonDict = Annotated[dict | None, BeforeValidator(parse_json_string)]
