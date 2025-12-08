import uuid
from functools import cache
from logging import getLogger
from pathlib import Path

from google.cloud import videointelligence
from google.cloud.storage import Client
from typing_extensions import override
from werkzeug.datastructures import FileStorage

from otel.default_tracer import get_default_tracer
from src.config.get_config import get_config
from src.message.google_video_intelligence.get_video_client import get_video_intelligence_client
from src.message.google_video_intelligence.video_intelligence_models import (
    GoogleVideoIntelligenceResponse,
    SkippedSafetyCheckResponse,
)
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.SafetyChecker import (
    SafetyChecker,
    SafetyCheckRequest,
)
from src.safety_queue.video_safety_handler import handle_video_safety_check

tracer = get_default_tracer()

features = [videointelligence.Feature.EXPLICIT_CONTENT_DETECTION]


@cache
def get_safety_bucket():
    bucket_name = get_config().google_cloud_services.safety_storage_bucket
    client = Client()
    return client.bucket(bucket_name)


def generate_random_filename(original_filename: str) -> str:
    extension = Path(original_filename).suffix
    random_name = f"{uuid.uuid4().hex}{extension}"
    return random_name


def upload_to_safety_bucket(file: FileStorage, client: GoogleCloudStorage):
    name = generate_random_filename(file.filename or ".unknown")

    upload_response = client.upload_content(
        filename=name, content=file, bucket_name=get_config().google_cloud_services.safety_storage_bucket
    )

    return upload_response.storage_path


def delete_from_safety_bucket(path: str, client: GoogleCloudStorage):
    """This function removes videos from the safety bucket after they are checked. Files delete after 1-day in the buckets as a fall back"""
    client.delete_file(path, bucket_name=get_config().google_cloud_services.safety_storage_bucket)


class GoogleVideoIntelligence(SafetyChecker):
    @override
    @tracer.start_as_current_span("GoogleVideoIntelligence.check_request")
    def check_request(self, req: SafetyCheckRequest):
        config = get_config()

        if (
            config.feature_flags.enable_blocking_video_safety_check
            or config.feature_flags.enable_queued_video_safety_check
        ):
            bucket_name = get_config().google_cloud_services.safety_storage_bucket
            video_client = get_video_intelligence_client()

            operation = video_client.annotate_video(
                request={
                    "features": features,
                    "input_uri": req.content,
                }
            )

            if config.feature_flags.enable_blocking_video_safety_check:
                result = operation.result(timeout=180)

                if isinstance(result, videointelligence.AnnotateVideoResponse):
                    return GoogleVideoIntelligenceResponse(result)

                msg = "Unexpected result from google video checker"
                raise TypeError(msg)

            if config.feature_flags.enable_queued_video_safety_check:
                getLogger().info("Queuing video safety check for operation %s", operation.operation.name)
                handle_video_safety_check.send(operation.operation.name)
                return SkippedSafetyCheckResponse()

        return SkippedSafetyCheckResponse()
