import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker
from dramatiq.middleware.asyncio import AsyncIO
from dramatiq.middleware.prometheus import Prometheus
from typing_extensions import override

from api.config import settings
from api.logging.setup import setup_logging
from api.otel.setup import setup_otel

# Dramatiq requires a broker to be set before actors are declared.
# This sets a stub so actor modules can be imported safely before setup_safety_queue() is called.
# https://github.com/Bogdanp/dramatiq/pull/762
dramatiq.set_broker(StubBroker())


class OtelMiddleware(dramatiq.Middleware):
    @override
    def after_worker_boot(self, broker: dramatiq.Broker, worker: dramatiq.Worker) -> None:
        setup_otel()


def setup_safety_queue() -> None:
    setup_logging(json_logs=settings.LOG_JSON_FORMAT, log_level=settings.LOG_LEVEL)

    redis_broker = RedisBroker(url=settings.SAFETY_QUEUE_URL, namespace="playground_safety_queue")

    old_broker = dramatiq.get_broker()
    for existing_actor_name in old_broker.get_declared_actors():
        actor = old_broker.get_actor(existing_actor_name)
        actor.broker = redis_broker
        redis_broker.declare_actor(actor)

    redis_broker.add_middleware(Prometheus())
    redis_broker.add_middleware(AsyncIO())
    redis_broker.add_middleware(OtelMiddleware())

    dramatiq.set_broker(redis_broker)
