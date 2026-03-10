from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SafetyCheckRequest:
    content: str
    name: str | None = None


class SafetyCheckResponse(ABC):
    @abstractmethod
    def is_safe(self) -> bool:
        raise NotImplementedError


class TextSafetyChecker(ABC):
    @abstractmethod
    async def check_request(self, request: SafetyCheckRequest) -> SafetyCheckResponse:
        raise NotImplementedError
