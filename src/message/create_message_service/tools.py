from pydantic import BaseModel
from pydantic_ai.tools import ToolDefinition


class Add(BaseModel):
    """Add two"""

    a: int
    b: int


def get_tools():
    return [
        ToolDefinition(
            name=Add.__name__.lower(), description=Add.__doc__, parameters_json_schema=Add.model_json_schema()
        )
    ]
