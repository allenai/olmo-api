from logging import getLogger

import dramatiq
from google.api_core.operation import Operation
from google.cloud.videointelligence_v1 import AnnotateVideoResponse

from src.message.google_video_intelligence.get_video_client import get_video_intelligence_client
from src.message.google_video_intelligence.video_intelligence_models import GoogleVideoIntelligenceResponse


class VideoIntelligenceOperationNotFinishedError(Exception): ...


def noop():
    pass


SAFETY_QUEUE_NAME = "safety"


@dramatiq.actor(queue_name=SAFETY_QUEUE_NAME)
def handle_video_safety_check(operation_name: str):
    getLogger().debug("Checking video safety check name %s", operation_name)
    video_client = get_video_intelligence_client()

    # Hacky but I couldn't find a better way to get an ops client https://stackoverflow.com/questions/71860530/how-do-i-poll-google-long-running-operations-using-python-library
    raw_operation = video_client.transport.operations_client.get_operation(operation_name)

    # Using this so we can have their result parsing without having to copy it ourselves
    operation = Operation(raw_operation, refresh=noop, cancel=noop, result_type=AnnotateVideoResponse)

    if not operation.done():
        raise VideoIntelligenceOperationNotFinishedError

    result = operation.result(0)

    # TODO: Handle the result instead of just returning
    if isinstance(result, AnnotateVideoResponse):
        mapped_response = GoogleVideoIntelligenceResponse(result)
        getLogger().debug(
            "Finished video safety check name %s, has violation: %s", operation_name, mapped_response.has_violation
        )

    msg = "Unexpected result from google video checker"
    raise TypeError(msg)
