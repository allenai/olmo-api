from abc import abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class SafetyCheckerType(StrEnum):
    GoogleLanguage = "google-moderate-text"
    GoogleVision = "google-vision-safe-search"


@dataclass
class SafetyCheckRequest:
    content: str
    name: str | None = None


class SafetyCheckResponse:
    @abstractmethod
    def is_safe(self) -> bool:
        raise NotImplementedError


class SafetyChecker:
    @abstractmethod
    def check_request(self, req: SafetyCheckRequest) -> SafetyCheckResponse:
        raise NotImplementedError
