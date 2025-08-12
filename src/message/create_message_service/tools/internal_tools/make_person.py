from typing import Any

from src.message.create_message_service.tools.tool_base import ToolBase


class MakePerson(ToolBase):
    """Adds a user to the db"""

    first_name: str
    last_name: str

    @staticmethod
    def call(args: str | dict[str, Any] | None):
        if isinstance(args, str):
            # TODO talk about how error these things...
            return "Error calling tool with incorrect params"

        if args is None:
            return "Args are none"

        return args["first_name"] + args["last_name"]
