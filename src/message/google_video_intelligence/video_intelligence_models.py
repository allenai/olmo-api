from google.cloud import videointelligence
from typing_extensions import override

from src.message.SafetyChecker import (
    SafetyCheckResponse,
)


class SkippedSafetyCheckResponse(SafetyCheckResponse):
    @override
    def is_safe(self) -> bool:
        return True


class GoogleVideoIntelligenceResponse(SafetyCheckResponse):
    response: videointelligence.AnnotateVideoResponse

    def __init__(self, response: videointelligence.AnnotateVideoResponse):
        self.response = response

    def is_safe(self) -> bool:
        return not self.has_violation()

    def has_violation(self) -> bool:
        if len(self.response.annotation_results) != 1:
            msg = "Unexpected multiple video response"
            raise TypeError(msg)

        return any(
            videointelligence.Likelihood(frame.pornography_likelihood)
            in {
                videointelligence.Likelihood.POSSIBLE,
                videointelligence.Likelihood.VERY_LIKELY,
                videointelligence.Likelihood.LIKELY,
            }
            for frame in self.response.annotation_results[0].explicit_annotation.frames
        )
