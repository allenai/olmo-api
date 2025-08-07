import logging
from typing import Any

from pydantic import BaseModel
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.tools import ToolDefinition

logging.basicConfig()
logging.getLogger().setLevel(logging.NOTSET)


class Add(BaseModel):
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

        return args["number_b"] + args["number_b"]


class Subtract(BaseModel):
    """Subract number_a - number_b"""

    number_a: int
    number_b: int

    @staticmethod
    def call(args: str | dict[str, Any] | None):
        if isinstance(args, str):
            # TODO talk about how error these things...
            return "Error calling tool with incorrect params"

        if args is None:
            return "Args are none"

        return args["number_b"] - args["number_b"]


def get_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name=Add.__name__.lower(), description=Add.__doc__, parameters_json_schema=Add.model_json_schema()
        ),
        ToolDefinition(
            name=Subtract.__name__.lower(),
            description=Subtract.__doc__,
            parameters_json_schema=Subtract.model_json_schema(),
        ),
    ]


def call_tool_function(tool_call: ToolCallPart):
    if tool_call.tool_name == Add.__name__.lower():
        return Add.call(tool_call.args)
    if tool_call.tool_name == Subtract.__name__.lower():
        return Subtract.call(tool_call.args)
    return ""


def call_tool(tool_call: ToolCallPart) -> ToolReturnPart:
    tool_response = call_tool_function(tool_call)
    # TODO respond with something else out of here shouldn't be toolreturn part

    return ToolReturnPart(tool_name=tool_call.tool_name, content=tool_response, tool_call_id=tool_call.tool_call_id)
