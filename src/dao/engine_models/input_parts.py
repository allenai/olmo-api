from enum import StrEnum
from typing import Literal, TypeAlias

from pydantic import Field

from src.api_interface import APIInterface

# We import PromptTemplate and ToolDefinition so Pydantic knows how to resolve them, preventing some model definition errors
from src.dao.engine_models.prompt_template import PromptTemplate  # noqa: F401
from src.dao.engine_models.tool_definitions import ToolDefinition  # noqa: F401


class PointPartType(StrEnum):
    MOLMO_2_INPUT_POINT = "molmo_2_input_point"


class Molmo2PointPart(APIInterface):
    type: Literal[PointPartType.MOLMO_2_INPUT_POINT] = Field(default=PointPartType.MOLMO_2_INPUT_POINT, init=False)
    x: int
    y: int
    time: float
    label: str = Field(default="object")


# Will be a union of different parts in the future
InputPart: TypeAlias = Molmo2PointPart
