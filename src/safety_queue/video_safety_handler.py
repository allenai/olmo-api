from logging import getLogger

import dramatiq
from google.api_core.operation import Operation
from google.cloud.videointelligence_v1 import AnnotateVideoResponse
from sqlalchemy import Engine, NullPool, create_engine
from sqlalchemy.orm import Session

from src.config.get_config import get_config
from src.dao.message.message_repository import MessageRepository
from src.db.init_sqlalchemy import make_psycopg3_url
from src.message.google_video_intelligence.get_video_client import get_video_intelligence_client
from src.message.google_video_intelligence.video_intelligence_models import GoogleVideoIntelligenceResponse
from src.message.GoogleCloudStorage import GoogleCloudStorage


class VideoIntelligenceOperationNotFinishedError(Exception): ...


class VideoIntelligenceOperationMessageNotFoundError(Exception): ...


def noop():
    pass


SAFETY_QUEUE_NAME = "safety"


def _make_worker_db_engine() -> Engine:
    config = get_config()
    url = make_psycopg3_url(config.db.conninfo)
    return create_engine(url, poolclass=NullPool)


logger = getLogger()


@dramatiq.actor(queue_name=SAFETY_QUEUE_NAME)
def handle_video_safety_check(operation_name: str, message_id: str):
    logger.debug("Checking video safety check name %s", operation_name)

    with Session(_make_worker_db_engine()) as session:
        video_client = get_video_intelligence_client()

        # Hacky but I couldn't find a better way to get an ops client https://stackoverflow.com/questions/71860530/how-do-i-poll-google-long-running-operations-using-python-library
        raw_operation = video_client.transport.operations_client.get_operation(operation_name)

        # Using this so we can have their result parsing without having to copy it ourselves
        operation = Operation(raw_operation, refresh=noop, cancel=noop, result_type=AnnotateVideoResponse)

        if not operation.done():
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

        if mapped_response.is_safe():
            if not message.harmful:
                message.harmful = mapped_response.is_safe()
                message_repository.update(message)

        else:
            # delete message and files
            storage_client = GoogleCloudStorage()
            if message.file_urls:
                config = get_config()
                storage_client.delete_multiple_files_by_url(
                    message.file_urls, bucket_name=config.google_cloud_services.storage_bucket
                )

        getLogger().debug(
            "Finished video safety check name %s, has violation: %s", operation_name, mapped_response.has_violation
        )
