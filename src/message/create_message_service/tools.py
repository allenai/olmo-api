import logging

from pydantic import BaseModel
from pydantic_ai.tools import ToolDefinition

logging.basicConfig()
logging.getLogger().setLevel(logging.NOTSET)


class Add(BaseModel):
    """Add two numbers together"""

    number_a: int
    number_b: int


def get_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name=Add.__name__.lower(), description=Add.__doc__, parameters_json_schema=Add.model_json_schema()
        ),
    ]
