import uuid
from functools import cache
from pathlib import Path

from google.cloud import videointelligence
from google.cloud.storage import Client
from werkzeug.datastructures import FileStorage

from otel.default_tracer import get_default_tracer
from src.config.get_config import get_config
from src.message.SafetyChecker import (
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
)

tracer = get_default_tracer()

features = [videointelligence.Feature.EXPLICIT_CONTENT_DETECTION]


@cache
def get_safety_bucket():
    bucket_name = get_config().google_cloud_services.safety_storage_bucket
    client = Client()
    return client.bucket(bucket_name)


@cache
def get_video_client():
    return videointelligence.VideoIntelligenceServiceClient()


def generate_random_filename(original_filename: str) -> str:
    extension = Path(original_filename).suffix
    random_name = f"{uuid.uuid4().hex}{extension}"
    return random_name


def upload_to_safety_bucket(file: FileStorage):
    name = generate_random_filename(file.filename or ".unkown")
    safe_bucket = get_safety_bucket()
    blob = safe_bucket.blob(name)
    file.seek(0)
    blob.upload_from_file(file.stream, content_type=file.content_type)
    file.seek(0)

    return name


def delete_from_safety_bucket(path: str):
    """This function removes videos from the safety bucket after they are checked. Files delete after 1-day in the buckets as a fall back"""
    safe_bucket = get_safety_bucket()
    blob = safe_bucket.blob(path)
    blob.delete()


class GoogleVideoIntelligenceResponse(SafetyCheckResponse):
    response: videointelligence.AnnotateVideoResponse

    def __init__(self, response: videointelligence.AnnotateVideoResponse):
        self.response = response

    def is_safe(self) -> bool:
        return not self.has_violation()

    def has_violation(self) -> bool:
        if len(self.response.annotation_results) != 1:
            msg = "Unexpected mulitiple video response"
            raise TypeError(msg)

        return any(
            videointelligence.Likelihood(frame.pornography_likelihood) == videointelligence.Likelihood.VERY_LIKELY
            for frame in self.response.annotation_results[0].explicit_annotation.frames
        )


class GoogleVideoIntelligence(SafetyChecker):
    @tracer.start_as_current_span("GoogleVideoIntelligence.check_request")
    def check_request(self, req: SafetyCheckRequest):
        bucket_name = get_config().google_cloud_services.safety_storage_bucket
        video_client = get_video_client()

        operation = video_client.annotate_video(
            request={
                "features": features,
                "input_uri": f"gs://{bucket_name}/{req.content}",
            }
        )

        result = operation.result(timeout=180)

        if isinstance(result, videointelligence.AnnotateVideoResponse):
            return GoogleVideoIntelligenceResponse(result)

        msg = "Unexpected result from google video checker"
        raise TypeError(msg)
