from functools import cached_property

from google.cloud.vision import (
    AnnotateImageRequest,
    AnnotateImageResponse,
    Feature,
    Image,
    ImageAnnotatorAsyncClient,
    Likelihood,
)
from opentelemetry import trace
from typing_extensions import override

from .safety_checker_base import (
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
    SafetyCheckUnsafeError,
)

tracer = trace.get_tracer(__name__)


class GoogleImageSafetyCheckResponse(SafetyCheckResponse):
    def __init__(self, response: AnnotateImageResponse, filename: str | None):
        self._response = response
        self.filename = filename

    @override
    def is_safe(self) -> bool:
        return len(self.get_violation_categories()) == 0

    def get_violation_categories(self) -> set[str]:
        violations: set[str] = set()

        if self._response.safe_search_annotation.adult is Likelihood.VERY_LIKELY:
            violations.add("adult")

        if self._response.safe_search_annotation.violence is Likelihood.VERY_LIKELY:
            violations.add("violence")

        if self._response.safe_search_annotation.racy is Likelihood.VERY_LIKELY:
            violations.add("racy")

        return violations


class GoogleImageSafetyChecker(SafetyChecker):
    @cached_property
    def client(self) -> ImageAnnotatorAsyncClient:
        return ImageAnnotatorAsyncClient()

    @tracer.start_as_current_span("GoogleImageSafetyChecker/check_request")
    @override
    async def check_request(self, request: SafetyCheckRequest, *, throw: bool = False) -> SafetyCheckResponse:
        span = trace.get_current_span()
        span.set_attribute("filename", request.name or "unknown")
        annotation_request = AnnotateImageRequest(
            image=Image(content=request.content), features=[Feature(type=Feature.Type.SAFE_SEARCH_DETECTION)]
        )

        operation = await self.client.batch_annotate_images(requests=[annotation_request])
        response = next(iter(operation.responses))

        safety_response = GoogleImageSafetyCheckResponse(response=response, filename=request.name)

        span.set_attributes({
            "is_safe": safety_response.is_safe(),
            "violation_categories": list(safety_response.get_violation_categories()),
        })

        if not safety_response.is_safe() and throw:
            raise SafetyCheckUnsafeError

        return safety_response
