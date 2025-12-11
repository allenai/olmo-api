import logging

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware.asyncio import AsyncIO
from dramatiq.middleware.prometheus import Prometheus
from opentelemetry_instrumentor_dramatiq import DramatiqInstrumentor  # type:ignore [import-untyped]
from typing_extensions import override

from otel.otel_setup import setup_otel
from src import util
from src.config.get_config import get_config


class LogFormatterMiddleware(dramatiq.Middleware):
    @override
    def after_worker_boot(self, broker: dramatiq.Broker, worker: dramatiq.Worker) -> None:
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.setFormatter(util.StackdriverJsonFormatter())


class OtelMiddleware(dramatiq.Middleware):
    @override
    def after_worker_boot(self, broker: dramatiq.Broker, worker: dramatiq.Worker) -> None:
        setup_otel()


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
    # redis_broker.add_middleware(LogFormatterMiddleware())
    # redis_broker.add_middleware(OtelMiddleware())

    dramatiq.set_broker(redis_broker)

    DramatiqInstrumentor().instrument()
