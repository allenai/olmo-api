from fastapi import FastAPI
from fastapi_problem.handler import add_exception_handler, new_exception_handler
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from src.config import settings
from src.health import health_router
from src.logging import StructLogMiddleware, setup_logging


def create_app() -> FastAPI:
    app = FastAPI(
        title="Playground API",
        version="0.1.0",
    )

    add_exception_handler(app, new_exception_handler())

    app.include_router(health_router)

    setup_logging(json_logs=settings.LOG_JSON_FORMAT, log_level=settings.LOG_LEVEL)
    app.add_middleware(StructLogMiddleware)

    FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()
