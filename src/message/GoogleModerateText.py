from time import time_ns

from flask import current_app
from google.cloud.language_v2 import (
    Document,
    LanguageServiceClient,
    ModerateTextRequest,
    ModerateTextResponse,
)

from src.api_interface import APIInterface
from src.config.get_config import get_config
from src.message.SafetyChecker import (
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
)


class ViolationInfo(APIInterface):
    category_name: str
    confidence: float
    confidence_threshold: float

    severity: float
    severity_threshold: float


class GoogleModerateTextResponse(SafetyCheckResponse):
    result: ModerateTextResponse
    confidence_threshold: float
    severity_threshold: float
    unsafe_violation_categories: list[str]

    def __init__(self, result: ModerateTextResponse):
        self.result = result

        config = get_config()
        self.confidence_threshold = config.google_moderate_text.default_confidence_threshold
        self.severity_threshold = config.google_moderate_text.default_severity_threshold
        self.unsafe_violation_categories = config.google_moderate_text.default_unsafe_violation_categories

    def is_safe(self) -> bool:
        violations = self.get_violations()

        return len(violations) == 0

    def get_violations(self) -> list[ViolationInfo]:
        return [
            ViolationInfo(
                category_name=category.name,
                confidence=category.confidence,
                confidence_threshold=self.confidence_threshold,
                severity=category.severity,
                severity_threshold=self.severity_threshold,
            )
            for category in self.result.moderation_categories
            if category.name in self.unsafe_violation_categories
            and category.confidence >= self.confidence_threshold
            and category.severity >= self.severity_threshold
        ]

    def get_scores(self):
        return [
            {"name": category.name, "confidence": category.confidence, "severity": category.severity}
            for category in self.result.moderation_categories
        ]


class GoogleModerateText(SafetyChecker):
    client: LanguageServiceClient

    def __init__(self):
        self.client = LanguageServiceClient(client_options={"api_key": get_config().google_cloud_services.api_key})

    def check_request(self, req: SafetyCheckRequest) -> SafetyCheckResponse:
        request = ModerateTextRequest(
            document=Document(content=req.content, type=Document.Type.PLAIN_TEXT), model_version="MODEL_VERSION_2"
        )

        start_ns = time_ns()
        result = self.client.moderate_text(request)
        end_ns = time_ns()

        response = GoogleModerateTextResponse(result)

        current_app.logger.info({
            "event": "safety-check.results",
            "checker": "GoogleModerateText",
            "prompt": req.content,
            "duration_ms": (end_ns - start_ns) / 1_000_000,
            "violations": [info.model_dump() for info in response.get_violations()],
            "scores": response.get_scores(),
        })

        return response
