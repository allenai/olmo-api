import atexit
import logging
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy.orm import sessionmaker

from otel.otel_setup import setup_otel
from src import db, util
from src.config import get_config
from src.db.init_sqlalchemy import make_db_engine
from src.fastapi_error_handlers import register_exception_handlers
from src.fastapi_json_response import CustomJSONResponse
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.v3 import create_v3_router
from src.v4 import create_v4_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events"""
    # Startup - only OTEL instrumentation and cleanup
    cfg = get_config.Config.load(os.environ.get("FLASK_CONFIG_PATH", get_config.DEFAULT_CONFIG_PATH))

    setup_otel()

    HTTPXClientInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    PsycopgInstrumentor().instrument(enable_commenter=True)

    # Initialize db_engine for OTEL instrumentation and cleanup
    dbc = db.Client.from_config(cfg.db)
    db_engine = make_db_engine(cfg.db, pool=dbc.pool, sql_alchemy=cfg.sql_alchemy)
    SQLAlchemyInstrumentor().instrument(engine=db_engine, enable_commenter=True)

    # Store db_engine for cleanup
    app.state.db_engine = db_engine

    # Register cleanup on exit
    atexit.register(dbc.close)

    yield

    # Shutdown
    app.state.db_engine.dispose()


def create_app() -> FastAPI:
    """FastAPI application factory"""
    app = FastAPI(
        title="OLMo API",
        description="Backend API for playground.allenai.org",
        version="4.0",
        lifespan=lifespan,
        default_response_class=CustomJSONResponse,
    )

    # Configure structlog for structured logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer() if not __debug__
                else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Health check endpoint
    @app.get("/health", status_code=204)
    async def health():
        return None

    # OpenTelemetry Instrumentation for FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Register routers
    app.include_router(create_v4_router())
    app.include_router(create_v3_router())

    # Configure logging
    # Will be set up with proper formatter in Phase 2
    cfg = get_config.get_config()
    if not __debug__:
        h = logging.StreamHandler()
        h.setFormatter(util.StackdriverJsonFormatter())
        logging.basicConfig(level=cfg.server.log_level, handlers=[h])
    else:
        logging.basicConfig(level=cfg.server.log_level)

    return app


app = create_app()
