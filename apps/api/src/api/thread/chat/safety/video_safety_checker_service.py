import uuid
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, UploadFile
from opentelemetry import trace

from api.config import settings
from api.gcs_dependency import GoogleCloudStorageDependency
from api.logging.fastapi_logger import FastAPIStructLogger

from .safety_checkers.google_video_safety_checker import GoogleVideoIntelligenceSafetyChecker
from .safety_checkers.safety_checker_base import SafetyChecker, SafetyCheckRequest

logger = FastAPIStructLogger()
tracer = trace.get_tracer(__name__)


@lru_cache
def get_video_safety_checker() -> SafetyChecker:
    return GoogleVideoIntelligenceSafetyChecker()


def generate_random_filename(original_filename: str) -> str:
    extension = Path(original_filename).suffix
    random_name = f"{uuid.uuid4().hex}{extension}"
    return random_name


class VideoSafetyCheckerService:
    def __init__(self, cloud_storage: GoogleCloudStorageDependency):
        self.cloud_storage = cloud_storage

    @tracer.start_as_current_span("VideoSafetyCheckerService/check_video_safety")
    async def check_video_safety(self, files: Sequence[UploadFile], message_id: str) -> bool:
        checker = get_video_safety_checker()

        for file in files:
            filename = ""
            try:
                filename = generate_random_filename(file.filename or ".unknown")

                await file.seek(0)
                response = await self.cloud_storage.upload_content(
                    filename=filename, file_data=await file.read(), bucket_name=settings.SAFTEY_GCS_UPLOAD_BUCKET
                )
                request = SafetyCheckRequest(message_id=message_id, content=response.storage_path, name=filename)

                result = await checker.check_request(request)

                # this handles the file deletion for the inline strategy
                if not result.is_safe():
                    await self.cloud_storage.delete_file(
                        response.storage_path, bucket_name=settings.SAFTEY_GCS_UPLOAD_BUCKET
                    )
                    return False

            except Exception as e:
                logger.exception(
                    "video_safety.error", filename=filename, message_id=message_id, original_filename=file.filename
                )
                return False
        return True


VideoSafetyCheckerServiceDependency = Annotated[VideoSafetyCheckerService, Depends()]
