from typing import Any

from src.message.create_message_service.tools.tool_base import ToolBase


class Add(ToolBase):
    """Add two numbers together number_a + number_b"""

    number_a: int
    number_b: int

    @staticmethod
    def call(args: str | dict[str, Any] | None):
        if isinstance(args, str):
            # TODO talk about how error these things...
            return "Error calling tool with incorrect params"

        if args is None:
            return "Args are none"

        return args["number_a"] + args["number_b"]
