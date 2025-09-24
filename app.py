import atexit
import logging
import os

from flask import Flask
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.trace import set_tracer_provider
from sqlalchemy.orm import sessionmaker
from werkzeug.middleware.proxy_fix import ProxyFix

from src import db, error, util, v3
from src.config import get_config
from src.dao.flask_sqlalchemy_session import flask_scoped_session
from src.db.init_sqlalchemy import make_db_engine
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.openapi import openapi_blueprint
from src.v4 import create_v4_blueprint


class CustomAttributeSpanProcessor(SpanProcessor):
    def on_start(self, span, parent_context=None):
        span.set_attributes({
            "service.name": "olmo-api",
        })

    def on_end(self, span):
        pass


def create_app():
    app = Flask(__name__)

    # Use ISO formatted datetimes
    app.json = util.CustomJSONProvider(app)

    cfg = get_config.Config.load(os.environ.get("FLASK_CONFIG_PATH", get_config.DEFAULT_CONFIG_PATH))

    resource = Resource.create({
        "service.name": "olmo-api",
        "service.hello": "world",
    })

    tracer_provider = TracerProvider(resource=resource)

    tracer_provider.add_span_processor(CustomAttributeSpanProcessor())

    if cfg.otel.collector_type == "local":
        tracer_provider.add_span_processor(span_processor=SimpleSpanProcessor(OTLPSpanExporter()))
    if cfg.otel.collector_type == "cloud":
        tracer_provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter(project_id="ai2-reviz")))

    set_tracer_provider(tracer_provider)

    FlaskInstrumentor().instrument_app(app)

    dbc = db.Client.from_config(cfg.db)
    db_engine = make_db_engine(cfg.db, pool=dbc.pool, sql_alchemy=cfg.sql_alchemy)
    session_maker = sessionmaker(db_engine, expire_on_commit=False, autoflush=True)
    flask_scoped_session(session_maker, app=app)

    atexit.register(dbc.close)

    @app.get("/health")
    def health():
        return "", 204

    storage_client = GoogleCloudStorage(bucket_name=cfg.google_cloud_services.storage_bucket)

    app.register_blueprint(v3.Server(dbc, storage_client), url_prefix="/v3", name="v3")
    app.register_blueprint(
        create_v4_blueprint(dbc=dbc, storage_client=storage_client, session_maker=session_maker),
        url_prefix="/v4",
        name="v4",
    )
    app.register_blueprint(openapi_blueprint, name="openapi")

    app.register_error_handler(Exception, error.handle)

    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=cfg.server.num_proxies,
        x_proto=cfg.server.num_proxies,
        x_host=cfg.server.num_proxies,
        x_port=cfg.server.num_proxies,
    )

    if not app.debug:
        h = logging.StreamHandler()
        h.setFormatter(util.StackdriverJsonFormatter())
        logging.basicConfig(level=cfg.server.log_level, handlers=[h])

    return app


app = create_app()
