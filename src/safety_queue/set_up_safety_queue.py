import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware.asyncio import AsyncIO
from dramatiq.middleware.prometheus import Prometheus
from opentelemetry_instrumentor_dramatiq import DramatiqInstrumentor  # type:ignore [import-untyped]

from src.config.get_config import get_config


def set_up_safety_queue() -> None:
    config = get_config()
    redis_broker = RedisBroker(url=config.queue_url, namespace="playground_safety_queue")

    old_broker = dramatiq.get_broker()
    # reconfigure actors to use the new broker
    for existing_actor_name in old_broker.get_declared_actors():
        actor = old_broker.get_actor(existing_actor_name)
        actor.broker = redis_broker
        redis_broker.declare_actor(actor)

    # Prometheus is used to set up an endpoint we can health check
    redis_broker.add_middleware(Prometheus())
    redis_broker.add_middleware(AsyncIO())

    dramatiq.set_broker(redis_broker)

    DramatiqInstrumentor().instrument()
