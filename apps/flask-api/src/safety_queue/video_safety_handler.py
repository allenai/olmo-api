from logging import getLogger
from pathlib import Path

import dramatiq
from google.api_core import operation_async  # type: ignore
from google.cloud.videointelligence_v1 import (
    AnnotateVideoProgress,
    AnnotateVideoResponse,
)
from opentelemetry import trace
from sqlalchemy import Engine, NullPool, create_engine
from sqlalchemy.orm import Session

from db.url import make_url
from src.config.get_config import get_config
from src.dao.message.message_repository import MessageRepository
from src.message.google_video_intelligence.get_video_client import (
    get_async_video_intelligence_client,
)
from src.message.google_video_intelligence.video_intelligence_models import (
    GoogleVideoIntelligenceResponse,
)
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.otel.default_tracer import get_default_tracer

tracer = get_default_tracer()


class VideoIntelligenceOperationNotAvailableError(Exception): ...


class VideoIntelligenceOperationNotFinishedError(Exception): ...


class VideoIntelligenceOperationMessageNotFoundError(Exception): ...


SAFETY_QUEUE_NAME = "safety"


def _make_worker_db_engine() -> Engine:
    config = get_config()
    url = make_url(config.db.conninfo)
    return create_engine(url, poolclass=NullPool)


logger = getLogger()


@dramatiq.actor
def handle_retry_exhausted(*args, **kwargs) -> None:
    # Logs retry limits so we can alert of off them
    logger.error(
        "Job reached retry limits",
        extra={
            "event": "queue.retry-exhausted",
            "job_args": str(args),
            "job_kwargs": str(kwargs),
        },
    )


@dramatiq.actor(
    queue_name=SAFETY_QUEUE_NAME,
    max_retries=5,
    on_retry_exhausted=handle_retry_exhausted.actor_name,
)
@tracer.start_as_current_span("handle_video_safety_check")
async def handle_video_safety_check(operation_name: str, message_id: str, safety_file_url: str) -> None:
    span = trace.get_current_span()
    span.set_attributes({
        "operationName": operation_name,
        "messageId": message_id,
        "safetyFileUrl": safety_file_url,
    })
    logger.info("Checking video safety check name %s", operation_name)

    with Session(_make_worker_db_engine()) as session:
        video_client = get_async_video_intelligence_client()

        # Hacky but I couldn't find a better way to get an ops client https://stackoverflow.com/questions/71860530/how-do-i-poll-google-long-running-operations-using-python-library
        raw_operation = await video_client.transport.operations_client.get_operation(operation_name)
        if raw_operation is None:
            span.set_status(
                trace.StatusCode.ERROR,
                f"Operation {operation_name} not found. The Operation endpoint may not have the operation yet.",
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
            raise VideoIntelligenceOperationNotAvailableError from e

        result = await operation.result()

        if not isinstance(result, AnnotateVideoResponse):
            msg = "Unexpected result from google video checker"
            raise TypeError(msg)

        mapped_response = GoogleVideoIntelligenceResponse(result)
        message_repository = MessageRepository(session)
        message = message_repository.get_message_by_id(message_id)

        if message is None:
            not_found_message = f"Message {message_id} not found when evaluating a video safety check"
            logger.error(
                not_found_message,
                extra={"operation": operation_name, "message_id": message_id},
            )
            raise VideoIntelligenceOperationMessageNotFoundError(not_found_message)

        if not message.harmful:
            message.harmful = not mapped_response.is_safe()

        if not mapped_response.is_safe():
            logger.info(
                "Message has an unsafe file, deleting files",
                extra={"message_id": message_id},
            )
            storage_client = GoogleCloudStorage()
            config = get_config()

            safety_file_name = Path(safety_file_url).parts[-1]

            storage_client.delete_file(
                filename=safety_file_name,
                bucket_name=config.google_cloud_services.safety_storage_bucket,
            )

            if message.file_urls:
                storage_client.delete_multiple_files_by_url(
                    message.file_urls,
                    bucket_name=config.google_cloud_services.storage_bucket,
                )
                message.file_urls = None

        message_repository.update(message)

        logger.info(
            "Finished video safety check",
            extra={
                "operation": operation_name,
                "is_safe": mapped_response.is_safe(),
                "message_id": message_id,
            },
        )
