import dramatiq
from dramatiq_pg import PostgresBroker
from psycopg_pool import ConnectionPool

from src.message.GoogleVideoIntelligence import get_video_client


def set_up_safety_queue_app(connection_pool: ConnectionPool) -> None:
    dramatiq.set_broker(PostgresBroker(pool=connection_pool))


@dramatiq.actor
def video_safety_check_result_handling(operation_name: str):
    video_client = get_video_client()

    operation = video_client.transport.operations_client.get_operation(operation_name)

    if operation.done:
        # handle error or result
        # https://docs.cloud.google.com/service-infrastructure/docs/service-management/reference/rpc/google.longrunning#operation
        ...
