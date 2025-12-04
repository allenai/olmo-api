import dramatiq
from dramatiq.brokers.redis import RedisBroker
from google.api_core.operation import Operation
from google.cloud.videointelligence_v1 import AnnotateVideoResponse

from src.config.get_config import get_config
from src.message.google_video_intelligence.get_video_client import get_video_intelligence_client
from src.message.google_video_intelligence.GoogleVideoIntelligence import GoogleVideoIntelligenceResponse


def set_up_safety_queue_app() -> None:
    config = get_config()
    redis_broker = RedisBroker(url=config.queue_url, namespace="playground_safety_queue")
    dramatiq.set_broker(redis_broker)


class VideoIntelligenceOperationNotFinishedError(Exception): ...


def noop():
    pass


@dramatiq.actor
def video_safety_check_result_handling(operation_name: str):
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
        return GoogleVideoIntelligenceResponse(result)

    msg = "Unexpected result from google video checker"
    raise TypeError(msg)
