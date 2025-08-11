from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolBase(BaseModel, ABC):
    @staticmethod
    @abstractmethod
    def call(args: str | dict[str, Any] | None) -> str:
        pass
