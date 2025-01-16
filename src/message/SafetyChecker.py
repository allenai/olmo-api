from abc import abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional


class SafetyCheckerType(StrEnum):
    GoogleLanguage = "google-moderate-text"
    GoogleVision = "google-safety-search"
    WildGuard = "wildguard"


@dataclass
class SafetyCheckRequest:
    content: str
    name: Optional[str] = None


class SafetyCheckResponse:
    @abstractmethod
    def is_safe(self) -> bool:
        raise NotImplementedError


class SafetyChecker:
    @abstractmethod
    def check_request(self, req: SafetyCheckRequest) -> SafetyCheckResponse:
        raise NotImplementedError
