from opentelemetry.trace import get_tracer

from api.config import settings


def get_default_tracer():
    return get_tracer(settings.OTEL_SERVICE_NAME)
