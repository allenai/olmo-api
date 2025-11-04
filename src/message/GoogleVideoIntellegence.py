import uuid
from pathlib import Path

from google.cloud import videointelligence
from google.cloud.storage import Bucket, Client
from werkzeug.datastructures import FileStorage

from src.config.get_config import get_config
from src.message.SafetyChecker import (
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
)

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
    # TODO TTL
    blob = safe_bucket.blob(generate_random_filename(file.filename or ".unkown"))
    file.seek(0)
    blob.upload_from_file(file.stream, content_type=file.content_type)
    file.seek(0)

    return f"gs://{bucket_name}/{blob.name}"


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
        operation = video_client.annotate_video(
            request={
                "features": features,
                "input_uri": req.content,
            }
        )

        result = operation.result(timeout=180)

        print(result)

        return GoogleVideoIntellegenceResponse()
