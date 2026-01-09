from fastapi import FastAPI
from fastapi_problem.handler import add_exception_handler, new_exception_handler
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from api.auth.auth_service import get_bearer_token_validator
from api.config import settings
from api.health import health_router
from api.logging import StructLogMiddleware, setup_logging
from api.v5 import v5_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Playground API",
        version="0.1.0",
    )

    add_exception_handler(app, new_exception_handler())

    app.include_router(health_router)
    app.include_router(v5_router)

    setup_logging(json_logs=settings.LOG_JSON_FORMAT, log_level=settings.LOG_LEVEL)
    app.add_middleware(StructLogMiddleware)

    FastAPIInstrumentor.instrument_app(app)

    # get the token validator on startup, causing the app to fail fast if there are issues
    get_bearer_token_validator()

    return app


app = create_app()
