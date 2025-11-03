from opentelemetry.trace import get_tracer

APP_TRACER_NAME = "olmo-api"


def get_default_tracer():
    return get_tracer(APP_TRACER_NAME)
