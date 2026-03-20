from functools import lru_cache
from pathlib import Path

import dramatiq
from google.api_core import operation_async
from google.cloud.videointelligence_v1 import (
    AnnotateVideoProgress,
    AnnotateVideoRequest,
    AnnotateVideoResponse,
    Feature,
    Likelihood,
    VideoIntelligenceServiceAsyncClient,
)
from opentelemetry import propagate, trace
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from typing_extensions import override

from api.async_message_repository.async_message_repository import AsyncMessageRepository
from api.config import settings
from api.gcs_dependency import get_google_cloud_storage
from api.logging.fastapi_logger import FastAPIStructLogger
from db.url import make_url

from .safety_checker_base import (
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
    SkippedSafetyCheckResponse,
)

logger = FastAPIStructLogger()
tracer = trace.get_tracer(__name__)

SAFETY_QUEUE_NAME = "safety-fastapi"
FEATURES = [Feature.EXPLICIT_CONTENT_DETECTION]


@lru_cache
def get_video_intelligence_client_async() -> VideoIntelligenceServiceAsyncClient:
    return VideoIntelligenceServiceAsyncClient()


@lru_cache
def _make_worker_db_engine() -> AsyncEngine:
    url = make_url(settings.DATABASE_URL)
    return create_async_engine(url, poolclass=NullPool)


@lru_cache
def _make_worker_sessionmaker():
    return async_sessionmaker(_make_worker_db_engine(), expire_on_commit=False)


class VideoIntelligenceOperationNotAvailableError(Exception): ...


class VideoIntelligenceOperationMessageNotFoundError(Exception): ...


class GoogleVideoIntelligenceResponse(SafetyCheckResponse):
    response: AnnotateVideoResponse

    def __init__(self, response: AnnotateVideoResponse):
        self.response = response

    @override
    def is_safe(self) -> bool:
        return not self.has_violation()

    def has_violation(self) -> bool:
        if len(self.response.annotation_results) != 1:
            msg = "Unexpected multiple video response"
            raise TypeError(msg)

        return any(
            Likelihood(frame.pornography_likelihood) == Likelihood.VERY_LIKELY
            for frame in self.response.annotation_results[0].explicit_annotation.frames
        )


class GoogleVideoIntelligenceSafetyChecker(SafetyChecker):
    @tracer.start_as_current_span("GoogleVideoIntelligenceSafetyChecker/check_request")
    @override
    async def check_request(self, request: SafetyCheckRequest, *, throw: bool = False) -> SafetyCheckResponse:
        span = trace.get_current_span()
        span.set_attributes({
            "message_id": request.message_id or "None",
            "filename": request.name or "None",
            "path": request.content,
        })

        if not request.message_id:
            message_id_required_message = "SafetyCheckRequest.message_id is required for Video Safety Check"
            raise ValueError(message_id_required_message)

        logger.info("video_safety.begin", filename=request.name, path=request.content, message_id=request.message_id)

        client = get_video_intelligence_client_async()
        annotated_request = AnnotateVideoRequest(features=FEATURES, input_uri=request.content)

        operation = await client.annotate_video(annotated_request)
        operation_name = operation.operation.name

        span.set_attribute("operation_name", operation_name)

        handle_video_safety_check.send(
            operation_name=operation_name, file_url=request.content, message_id=request.message_id
        )

        return SkippedSafetyCheckResponse()


@dramatiq.actor
async def handle_retry_exhausted(failed_message: dict, retry_info: dict):
    kwargs: dict = failed_message.get("kwargs", {})
    operation_name: str = kwargs.get("operation_name", "unknown")
    file_url: str = kwargs.get("file_url", "unknown")
    message_id: str = kwargs.get("message_id", "unknown")

    carrier = failed_message.get("options", {}).get("otel_context", {})
    ctx = propagate.extract(carrier)
    with tracer.start_as_current_span("handle_retry_exhausted", context=ctx) as span:
        span.set_attributes({
            "operation_name": operation_name,
            "file_url": file_url,
            "message_id": message_id,
            "retries": retry_info.get("retries", 0),
        })
        span.set_status(trace.StatusCode.ERROR, "video safety check retries exhausted")

        logger.error(
            "video_safety_worker.retry_exhausted",
            operation_name=operation_name,
            file_url=file_url,
            message_id=message_id,
            retries=retry_info.get("retries"),
            max_retries=retry_info.get("max_retries"),
            traceback=failed_message.get("options", {}).get("traceback"),
        )

        storage_client = get_google_cloud_storage()
        safety_file_name = Path(file_url).parts[-1]

        await storage_client.delete_file(filename=safety_file_name, bucket_name=settings.SAFTEY_GCS_UPLOAD_BUCKET)

        await storage_client.delete_prefix(prefix=message_id, bucket_name=settings.USER_CONTENT_BUCKET)

        Session = _make_worker_sessionmaker()  # noqa: N806
        async with Session() as session:
            message_repository = AsyncMessageRepository(session)
            message = await message_repository.get_message_by_id(message_id)
            if message is not None:
                message.harmful = True
                message.file_urls = None
                await message_repository.update(message)
                await session.commit()


@dramatiq.actor(
    queue_name=SAFETY_QUEUE_NAME,
    max_retries=5,
    on_retry_exhausted=handle_retry_exhausted.actor_name,
)
@tracer.start_as_current_span("handle_video_safety_check")
async def handle_video_safety_check(operation_name: str, file_url: str, message_id: str):
    span = trace.get_current_span()
    span.set_attributes({
        "operation_name": operation_name,
        "message_id": message_id,
        "safety_file_url": file_url,
    })

    logger.info("video_safety.worker", message_id=message_id, file_url=file_url)

    Session = _make_worker_sessionmaker()  # noqa: N806
    async with Session() as session:
        video_client = get_video_intelligence_client_async()

        # Hacky but I couldn't find a better way to get an ops client https://stackoverflow.com/questions/71860530/how-do-i-poll-google-long-running-operations-using-python-library
        raw_operation = await video_client.transport.operations_client.get_operation(operation_name)
        if raw_operation is None:
            span.set_status(
                trace.StatusCode.ERROR,
                f"Operation {operation_name} not found. The Operation endpoint may not have the operation yet.",
            )
            logger.warning(
                "video_safety.operation_not_available",
                operation_name=operation_name,
                message_id=message_id,
            )
            raise VideoIntelligenceOperationNotAvailableError

        try:
            operation = operation_async.from_gapic(
                operation=raw_operation,
                operations_client=video_client.transport.operations_client,
                result_type=AnnotateVideoResponse,
                metadata_type=AnnotateVideoProgress,
            )
        except AttributeError as e:
            span.set_status(
                trace.StatusCode.ERROR,
                f"Operation {operation_name} not found or not done. The Operation endpoint may not have the operation yet.",
            )
            logger.warning(
                "video_safety.operation_not_available",
                operation_name=operation_name,
                message_id=message_id,
            )
            raise VideoIntelligenceOperationNotAvailableError from e

        result = await operation.result()

        if not isinstance(result, AnnotateVideoResponse):
            msg = "Unexpected result from google video checker"
            span.set_status(trace.StatusCode.ERROR, msg)
            raise TypeError(msg)

        mapped_response = GoogleVideoIntelligenceResponse(result)
        span.set_attribute("is_safe", mapped_response.is_safe())

        message_repository = AsyncMessageRepository(session)
        message = await message_repository.get_message_by_id(message_id)

        if message is None:
            not_found_message = f"Message {message_id} not found when evaluating a video safety check"
            span.set_status(trace.StatusCode.ERROR, not_found_message)
            logger.warning(
                "video_safety.message_not_found",
                operation=operation_name,
                message_id=message_id,
            )
            raise VideoIntelligenceOperationMessageNotFoundError(not_found_message)

        if not message.harmful:
            message.harmful = not mapped_response.is_safe()

        if not mapped_response.is_safe():
            logger.info(
                "video_safety.unsafe",
                file_url=file_url,
                message_id=message_id,
            )

            storage_client = get_google_cloud_storage()
            safety_file_name = Path(file_url).parts[-1]

            await storage_client.delete_file(
                filename=safety_file_name,
                bucket_name=settings.SAFTEY_GCS_UPLOAD_BUCKET,
            )

            await storage_client.delete_prefix(prefix=message_id, bucket_name=settings.USER_CONTENT_BUCKET)
            message.file_urls = None

        await message_repository.update(message)
        await session.commit()

        logger.info(
            "video_safety.complete",
            operation_name=operation_name,
            is_safe=mapped_response.is_safe(),
            message_id=message_id,
        )
