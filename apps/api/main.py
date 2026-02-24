from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi_problem.handler import add_exception_handler, new_exception_handler
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from api.auth.auth_service import get_bearer_token_validator
from api.config import settings
from api.db.sqlalchemy_engine import get_sqlalchemy_engine
from api.health import health_router
from api.logging import StructLogMiddleware, setup_logging
from api.otel.setup import setup_otel
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

    app.add_middleware(CorrelationIdMiddleware)

    setup_otel()

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(
        engine=get_sqlalchemy_engine().sync_engine,  # "sync-style" engine for async SQLAlchemy
        enable_commenter=True,
    )

    # get the token validator on startup, causing the app to fail fast if there are issues
    get_bearer_token_validator()

    return app


app = create_app()
