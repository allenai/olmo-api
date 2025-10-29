import requests
from flask import current_app
from google.cloud.vision import Likelihood, SafeSearchAnnotation

from src.config import get_config
from src.message.SafetyChecker import (
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
)


class GoogleVisionSafeSearchResponse(SafetyCheckResponse):
    response: requests.Response
    result: SafeSearchAnnotation

    def __init__(self, response: requests.Response):
        self.response = response
        target_result = response.json()["responses"][0]["safeSearchAnnotation"]
        self.result = SafeSearchAnnotation(mapping=target_result)

    def is_safe(self) -> bool:
        return len(self.get_violation_categories()) == 0

    def get_violation_categories(self) -> list[str]:
        violations = []

        if self.result.adult is Likelihood.VERY_LIKELY:
            violations.append("adult")

        if self.result.racy is Likelihood.VERY_LIKELY:
            violations.append("racy")

        if self.result.violence is Likelihood.VERY_LIKELY:
            violations.append("violence")

        return violations


class GoogleVisionSafeSearch(SafetyChecker):
    def check_request(self, req: SafetyCheckRequest):
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": get_config.cfg.google_cloud_services.api_key,
        }

        request = {
            "requests": [
                {
                    "image": {"content": req.content},
                    "features": [{"type": "SAFE_SEARCH_DETECTION"}],
                }
            ]
        }

        result = requests.post(
            url="https://vision.googleapis.com/v1/images:annotate",
            headers=headers,
            json=request,
        )

        if not result.ok:
            result.raise_for_status()

        response = GoogleVisionSafeSearchResponse(result)

        current_app.logger.info({
            "checker": "GoogleVisionSafeSearch",
            "request": req.name,
            "duration_ms": result.elapsed / 1_000_000,
            "violations": response.get_violation_categories(),
        })

        return response
