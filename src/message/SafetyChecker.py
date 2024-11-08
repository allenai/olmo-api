from abc import abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class SafetyCheckerType(StrEnum):
    Google = "google-moderate-text"
    WildGuard = "wildguard"


@dataclass
class SafetyCheckRequest:
    text: str


class SafetyCheckResponse:
    @abstractmethod
    def is_safe(self) -> bool:
        raise NotImplementedError


class SafetyChecker:
    @abstractmethod
    def check_request(self, req: SafetyCheckRequest) -> SafetyCheckResponse:
        raise NotImplementedError
