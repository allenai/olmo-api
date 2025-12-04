import dramatiq
from dramatiq.brokers.redis import RedisBroker

from src.config.get_config import get_config


def set_up_safety_queue() -> None:
    config = get_config()
    redis_broker = RedisBroker(url=config.queue_url, namespace="playground_safety_queue")
    dramatiq.set_broker(redis_broker)
