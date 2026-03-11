import asyncio
import base64
from collections.abc import Sequence
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, UploadFile
from opentelemetry import trace

from api.logging.fastapi_logger import FastAPIStructLogger
from api.thread.chat.safety.safety_checkers.google_image_safety_checker import GoogleImageSafetyChecker
from api.thread.chat.safety.safety_checkers.safety_checker_base import (
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
    SafetyCheckUnsafeError,
)

logger = FastAPIStructLogger()
tracer = trace.get_tracer(__name__)


@lru_cache
def get_imaage_safety_checker() -> SafetyChecker:
    return GoogleImageSafetyChecker()


ImageSafetyCheckerDependecy = Annotated[SafetyChecker, Depends(get_imaage_safety_checker)]


class ImageSafetyCheckerService:
    def __init__(self, checker: ImageSafetyCheckerDependecy):
        self._checker = checker

    # outside of class?
    @staticmethod
    async def _request_for_file(file: UploadFile) -> SafetyCheckRequest:
        image_contents = base64.b64encode(await file.read()).decode("utf-8")
        await file.seek(0)
        return SafetyCheckRequest(content=image_contents, name=file.filename)

    @tracer.start_as_current_span("VideoSafetyCheckerService/check_video_safety")
    async def check_image_safety(self, files: Sequence[UploadFile]) -> bool | None:
        span = trace.get_current_span()
        tasks: list[asyncio.Task[SafetyCheckResponse]] = []
        try:
            async with asyncio.TaskGroup() as tg:
                for file in files:
                    task = tg.create_task(
                        self._checker.check_request(
                            SafetyCheckRequest(
                                content=base64.b64encode(await file.read()).decode("utf-8"),
                                name=file.filename,
                            ),
                            throw=True,
                        )
                    )
                    tasks.append(task)
            return True
        except* SafetyCheckUnsafeError:
            pass
        except* Exception as e:
            span.record_exception(e)
            logger.exception("image_safety.exception")

        return False


ImageSafetyCheckerServiceDependency = Annotated[ImageSafetyCheckerService, Depends()]
