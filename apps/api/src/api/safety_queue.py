import dramatiq
import structlog
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker
from dramatiq.middleware.asyncio import AsyncIO
from dramatiq.middleware.prometheus import Prometheus
from opentelemetry import context, propagate, trace
from typing_extensions import override

from api.config import settings
from api.logging.fastapi_logger import FastAPIStructLogger
from api.logging.setup import setup_logging
from api.otel.setup import setup_otel

# Dramatiq requires a broker to be set before actors are declared.
# This sets a stub so actor modules can be imported safely before setup_safety_queue() is called.
# https://github.com/Bogdanp/dramatiq/pull/762
dramatiq.set_broker(StubBroker())
logger = FastAPIStructLogger()

SAFETY_QUEUE_NAMESPACE = "playground_api_safety_queue"


class OtelMiddleware(dramatiq.Middleware):
    @override
    def after_worker_boot(self, broker: dramatiq.Broker, worker: dramatiq.Worker) -> None:
        setup_otel()

    @override
    def before_enqueue(self, broker: dramatiq.Broker, message: dramatiq.Message, delay: int) -> None:
        if "otel_context" not in message.options:
            carrier: dict = {}
            propagate.inject(carrier)
            message.options["otel_context"] = carrier

    @override
    def before_process_message(self, broker: dramatiq.Broker, message: dramatiq.MessageProxy) -> None:
        # Context is in message.options for a regular dramatiq actor
        # or in the message.kwargs.failed_message.options for retry_exhausted actor
        carrier = message.options.get("otel_context") or (
            message.kwargs.get("failed_message", {}).get("options", {}).get("otel_context", {})
        )

        ctx = propagate.extract(carrier)
        token = context.attach(ctx)
        message.options["_otel_token"] = token

        structlog.contextvars.clear_contextvars()
        span_ctx = trace.get_current_span().get_span_context()
        if span_ctx.is_valid:
            structlog.contextvars.bind_contextvars(
                trace_id=format(span_ctx.trace_id, "032x"),
                span_id=format(span_ctx.span_id, "016x"),
                trace_flags=span_ctx.trace_flags,
            )

    @override
    def after_process_message(
        self, broker: dramatiq.Broker, message: dramatiq.MessageProxy, *, result=None, exception=None
    ) -> None:
        token = message.options.pop("_otel_token", None)
        if token is not None:
            context.detach(token)
        structlog.contextvars.clear_contextvars()

    @override
    def after_skip_message(self, broker: dramatiq.Broker, message: dramatiq.MessageProxy) -> None:
        token = message.options.pop("_otel_token", None)
        if token is not None:
            context.detach(token)
        structlog.contextvars.clear_contextvars()


def setup_safety_queue() -> None:
    setup_logging(json_logs=settings.LOG_JSON_FORMAT, log_level=settings.LOG_LEVEL)

    if not settings.SAFETY_QUEUE_ENABLED:
        return

    redis_broker = RedisBroker(url=settings.SAFETY_QUEUE_URL, namespace=SAFETY_QUEUE_NAMESPACE)

    old_broker = dramatiq.get_broker()
    for existing_actor_name in old_broker.get_declared_actors():
        actor = old_broker.get_actor(existing_actor_name)
        actor.broker = redis_broker
        redis_broker.declare_actor(actor)

    redis_broker.add_middleware(Prometheus())
    redis_broker.add_middleware(OtelMiddleware())
    redis_broker.add_middleware(AsyncIO())

    dramatiq.set_broker(redis_broker)
