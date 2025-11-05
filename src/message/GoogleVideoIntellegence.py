import uuid
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
bucket_name = get_config().google_cloud_services.safety_storage_bucket
client = Client()
safe_bucket = client.bucket(bucket_name)

video_client = videointelligence.VideoIntelligenceServiceClient()
features = [videointelligence.Feature.EXPLICIT_CONTENT_DETECTION]


def generate_random_filename(original_filename: str) -> str:
    extension = Path(original_filename).suffix
    random_name = f"{uuid.uuid4().hex}{extension}"
    return random_name


def upload_to_safety_bucket(file: FileStorage):
    name = generate_random_filename(file.filename or ".unkown")
    blob = safe_bucket.blob(name)
    file.seek(0)
    blob.upload_from_file(file.stream, content_type=file.content_type)
    file.seek(0)

    return name


def delete_from_safety_bucket(path: str):
    """This function removes videos from the safety bucket after they are checked. Files delete after 1-day in the buckets as a fall back"""
    blob = safe_bucket.blob(path)
    blob.delete()


class GoogleVideoIntellegenceResponse(SafetyCheckResponse):
    def __init__(self):
        pass

    def is_safe(self) -> bool:
        return False

    def get_violation_categories(self) -> list[str]:
        violations = []
        return violations

    # if self.result.adult is Likelihood.VERY_LIKELY:
    #     violations.append("adult")

    # if self.result.racy is Likelihood.VERY_LIKELY:
    #     violations.append("racy")

    # if self.result.violence is Likelihood.VERY_LIKELY:
    #     violations.append("violence")

    # return violations


class GoogleVideoIntellegence(SafetyChecker):
    def check_request(self, req: SafetyCheckRequest):
        with tracer.start_as_current_span("video annotate"):
            operation = video_client.annotate_video(
                request={
                    "features": features,
                    "input_uri": f"gs://{bucket_name}/{req.content}",
                }
            )

            result = operation.result(timeout=180)

            print(result)

            return GoogleVideoIntellegenceResponse()
