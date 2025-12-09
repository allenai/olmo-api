from logging import getLogger
from pathlib import Path

import dramatiq
from google.api_core.operation import Operation
from google.cloud.videointelligence_v1 import AnnotateVideoResponse
from opentelemetry import trace
from sqlalchemy import Engine, NullPool, create_engine
from sqlalchemy.orm import Session

from otel.default_tracer import get_default_tracer
from src.config.get_config import get_config
from src.dao.message.message_repository import MessageRepository
from src.db.init_sqlalchemy import make_psycopg3_url
from src.message.google_video_intelligence.get_video_client import get_video_intelligence_client
from src.message.google_video_intelligence.video_intelligence_models import GoogleVideoIntelligenceResponse
from src.message.GoogleCloudStorage import GoogleCloudStorage

tracer = get_default_tracer()


class VideoIntelligenceOperationNotAvailableError(Exception): ...


class VideoIntelligenceOperationNotFinishedError(Exception): ...


class VideoIntelligenceOperationMessageNotFoundError(Exception): ...


def noop():
    pass


SAFETY_QUEUE_NAME = "safety"


def _make_worker_db_engine() -> Engine:
    config = get_config()
    # For some reason "autosave" works in the main application but not here
    url = make_psycopg3_url(config.db.conninfo).difference_update_query(["autosave"])
    return create_engine(url, poolclass=NullPool)


logger = getLogger()


@dramatiq.actor(queue_name=SAFETY_QUEUE_NAME)
@tracer.start_as_current_span("handle_video_safety_check")
def handle_video_safety_check(operation_name: str, message_id: str, safety_file_url: str):
    span = trace.get_current_span()
    span.set_attributes({"operationName": operation_name, "messageId": message_id, "safetyFileUrl": safety_file_url})
    logger.info("Checking video safety check name %s", operation_name)

    with Session(_make_worker_db_engine()) as session:
        video_client = get_video_intelligence_client()

        # Hacky but I couldn't find a better way to get an ops client https://stackoverflow.com/questions/71860530/how-do-i-poll-google-long-running-operations-using-python-library
        raw_operation = video_client.transport.operations_client.get_operation(operation_name)
        if raw_operation is None:
            span.set_status(trace.StatusCode.ERROR, f"Operation {operation_name} not found")
            raise VideoIntelligenceOperationNotAvailableError

            # Using this so we can have their result parsing without having to copy it ourselves
        try:
            operation = Operation(raw_operation, refresh=noop, cancel=noop, result_type=AnnotateVideoResponse)
        except AttributeError as e:
            span.set_status(trace.StatusCode.ERROR, f"Operation {operation_name} not found or not done")
            raise VideoIntelligenceOperationMessageNotFoundError from e

        if not operation.done():
            span.add_event(
                "video-safety-operation-not-finished",
                {"operationName": operation_name, "messageId": message_id, "safetyFileUrl": safety_file_url},
            )
            raise VideoIntelligenceOperationNotFinishedError

        result = operation.result(0)

        if not isinstance(result, AnnotateVideoResponse):
            msg = "Unexpected result from google video checker"
            raise TypeError(msg)

        mapped_response = GoogleVideoIntelligenceResponse(result)
        message_repository = MessageRepository(session)
        message = message_repository.get_message_by_id(message_id)

        if message is None:
            not_found_message = f"Message {message_id} not found when evaluating a video safety check"
            logger.error(not_found_message)
            raise VideoIntelligenceOperationMessageNotFoundError(not_found_message)

        if not message.harmful:
            message.harmful = not mapped_response.is_safe()
            message_repository.update(message)

        if not mapped_response.is_safe():
            logger.info("Message %s has an unsafe file, deleting", message_id)
            storage_client = GoogleCloudStorage()
            config = get_config()

            safety_file_name = Path(safety_file_url).parts[-1]

            storage_client.delete_file(
                filename=safety_file_name, bucket_name=config.google_cloud_services.safety_storage_bucket
            )

            if message.file_urls:
                storage_client.delete_multiple_files_by_url(
                    message.file_urls, bucket_name=config.google_cloud_services.storage_bucket
                )

        logger.info("Finished video safety check name %s, is safe: %s", operation_name, mapped_response.is_safe())
