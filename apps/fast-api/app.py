from fastapi import FastAPI
from fastapi_problem.handler import add_exception_handler, new_exception_handler
from fastapi_structlog import setup_logger
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from src.config import settings
from src.health import health_router
from src.logging import add_logging_middlware
from src.v5 import v5_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Playground API",
        version="0.1.0",
    )

    add_exception_handler(app, new_exception_handler())

    app.include_router(health_router)
    app.include_router(v5_router)

    setup_logger(settings.log)
    add_logging_middlware(app)

    FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()
