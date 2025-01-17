from google.cloud.language_v2 import (
    LanguageServiceClient,
    Document,
    ModerateTextRequest,
    ModerateTextResponse,
)
from flask import current_app
from time import time_ns
from src import config
from src.message.SafetyChecker import (
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
)


class GoogleModerateTextResponse(SafetyCheckResponse):
    result: ModerateTextResponse
    threshold = 0.75
    unsafe_violation_categories = [
        "Toxic",
        "Derogatory",
        "Violent",
        "Sexual",
        "Insult",
        "Profanity",
        "Death, Harm & Tragedy",
        "Firearms & Weapons",
        "Public Safety",
        "Illicit Drugs",
        "War & Conflict",
        "Legal",
    ]

    def __init__(self, result: ModerateTextResponse):
        self.result = result

    def is_safe(self) -> bool:
        violations = self.get_violation_categories()

        return len(violations) == 0

    def get_violation_categories(self) -> list[str]:
        violations = []

        for category in self.result.moderation_categories:
            if (
                category.name in self.unsafe_violation_categories
                and category.confidence >= self.threshold
            ):
                violations.append(category.name)

        return violations


class GoogleModerateText(SafetyChecker):
    client: LanguageServiceClient

    def __init__(self):
        self.client = LanguageServiceClient(
            client_options={"api_key": config.cfg.google_cloud_services.api_key}
        )

    def check_request(self, req: SafetyCheckRequest) -> SafetyCheckResponse:
        request = ModerateTextRequest(
            document=Document(content=req.content, type=Document.Type.PLAIN_TEXT)
        )

        start_ns = time_ns()
        result = self.client.moderate_text(request)
        end_ns = time_ns()

        response = GoogleModerateTextResponse(result)

        current_app.logger.info(
            {
                "checker": "GoogleModerateText",
                "prompt": req.content,
                "duration_ms": (end_ns - start_ns) / 1_000_000,
                "violations": response.get_violation_categories(),
            }
        )

        return response
