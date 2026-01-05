from enum import StrEnum
from typing import Literal, TypeAlias

from core.api_interface import APIInterface
from pydantic import Field


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
