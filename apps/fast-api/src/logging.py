from asgi_correlation_id.middleware import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi_structlog.middleware import (
    AccessLogMiddleware,
    CurrentScopeSetMiddleware,
    StructlogMiddleware,
)


def add_logging_middlware(app: FastAPI) -> None:
    app.add_middleware(CurrentScopeSetMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(StructlogMiddleware)
    app.add_middleware(AccessLogMiddleware)
