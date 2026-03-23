from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import override


@dataclass(kw_only=True)
class SafetyCheckRequest:
    content: str
    name: str | None = None
    message_id: str | None = None


class SafetyCheckResponse(ABC):
    @abstractmethod
    def is_safe(self) -> bool:
        raise NotImplementedError


class SkippedSafetyCheckResponse(SafetyCheckResponse):
    @override
    def is_safe(self) -> bool:
        return True


class SafetyCheckUnsafeError(Exception): ...


class SafetyChecker(ABC):
    @abstractmethod
    async def check_request(self, request: SafetyCheckRequest, *, throw: bool = False) -> SafetyCheckResponse:
        raise NotImplementedError
