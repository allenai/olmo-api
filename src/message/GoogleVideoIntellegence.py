from google.cloud import videointelligence
from google.cloud.storage import Bucket, Client
from src.config.get_config import get_config

from src.message.SafetyChecker import (
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
)

client = Client()
safe_bucket = client.bucket(get_config().google_cloud_services.safety_storage_bucket)

video_client = videointelligence.VideoIntelligenceServiceClient()
features = [videointelligence.Feature.EXPLICIT_CONTENT_DETECTION]


class GoogleVideoIntellegence(SafetyChecker):
    def check_request(self, req: SafetyCheckRequest):
        operation = video_client.annotate_video(
            request={
                "features": features,
                "input_uri": req.content,
            }
        )

        result = operation.result(timeout=180)


def upload_to_safety_bucket(file: str):
    blob = safe_bucket.blob(file.split("/")[-1])
    blob.upload_from_filename(file)

    return blob.path
