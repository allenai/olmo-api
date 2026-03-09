from dataclasses import dataclass, field
from functools import cached_property
from time import time_ns
from typing import override

from google.cloud.language_v2 import Document, LanguageServiceAsyncClient, ModerateTextRequest, ModerateTextResponse
from opentelemetry import trace

from api.logging.fastapi_logger import FastAPIStructLogger
from core import APIInterface

from .safety_checker_base import (
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
)

logger = FastAPIStructLogger()

tracer = trace.get_tracer(__name__)


# more configurable?
@dataclass(kw_only=True)
class GoogleTextSafetySettings:
    confidence_threshold: float = field(default=0.8)
    severity_threshold: float = field(default=0.7)
    unsafe_violation_categories: list[str] = field(
        default_factory=lambda: [
            "Toxic",
            "Derogatory",
            "Violent",
            "Sexual",
            "Insult",
            "Profanity",
            "Death, Harm & Tragedy",
            "Firearms & Weapons",
            "Public Safety",
            "War & Conflict",
            "Dangerous Content",
        ]
    )


class ViolationInfo(APIInterface):
    category_name: str
    confidence: float
    confidence_threshold: float

    severity: float
    severity_threshold: float


class GoogleSafetyCheckResponse(SafetyCheckResponse):
    result: ModerateTextResponse
    safety_settings: GoogleTextSafetySettings

    def __init__(self, result: ModerateTextResponse):
        self.result = result
        self.safety_settings = GoogleTextSafetySettings()  # do we need to load from somewhere

    def is_safe(self) -> bool:
        violations = self.get_violations()

        return len(violations) == 0

    def get_violations(self) -> list[ViolationInfo]:
        return [
            ViolationInfo(
                category_name=category.name,
                confidence=category.confidence,
                confidence_threshold=self.safety_settings.confidence_threshold,
                severity=category.severity,
                severity_threshold=self.safety_settings.severity_threshold,
            )
            for category in self.result.moderation_categories
            if category.name in self.safety_settings.unsafe_violation_categories
            and category.confidence >= self.safety_settings.confidence_threshold
            and category.severity >= self.safety_settings.severity_threshold
        ]

    def get_scores(self):
        return [
            {
                "name": category.name,
                "confidence": category.confidence,
                "severity": category.severity,
            }
            for category in self.result.moderation_categories
        ]


class GoogleTextSafetyChecker(SafetyChecker):
    # defer creation of client until inside the thread loop
    @cached_property
    def client(self) -> LanguageServiceAsyncClient:
        return LanguageServiceAsyncClient()

    @tracer.start_as_current_span(name="GoogleTextSafetyChecker/check_request")
    @override
    async def check_request(self, request: SafetyCheckRequest) -> SafetyCheckResponse:
        span = trace.get_current_span()
        moderate_text_request = ModerateTextRequest(
            document=Document(content=request.content, type=Document.Type.PLAIN_TEXT),
            model_version="MODEL_VERSION_2",
        )

        start_ns = time_ns()
        result = await self.client.moderate_text(moderate_text_request)
        end_ns = time_ns()

        response = GoogleSafetyCheckResponse(result)
        span.set_attributes({
            "duration_ms": (end_ns - start_ns) / 1_000_000,
            "violations": [violation.model_dump_json() for violation in response.get_violations()],
            "scores": [str(score) for score in response.get_scores()],
        })

        return response
