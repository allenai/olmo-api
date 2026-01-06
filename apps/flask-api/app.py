import atexit
import logging
import os

from flask import Flask
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy.orm import sessionmaker
from werkzeug.middleware.proxy_fix import ProxyFix

from src import db, error, util, v3
from src.config import get_config
from src.dao.flask_sqlalchemy_session import flask_scoped_session
from src.db.init_sqlalchemy import make_db_engine
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.openapi import openapi_blueprint
from src.otel.otel_setup import setup_otel
from src.safety_queue.set_up_safety_queue import set_up_safety_queue
from src.v4 import create_v4_blueprint


def create_app():
    app = Flask(__name__)

    # Use ISO formatted datetimes
    app.json = util.CustomJSONProvider(app)

    cfg = get_config.Config.load(os.environ.get("FLASK_CONFIG_PATH", get_config.DEFAULT_CONFIG_PATH))

    setup_otel()

    FlaskInstrumentor().instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    PsycopgInstrumentor().instrument(enable_commenter=True)

    set_up_safety_queue()

    dbc = db.Client.from_config(cfg.db)
    db_engine = make_db_engine(cfg.db, pool=dbc.pool)
    SQLAlchemyInstrumentor().instrument(engine=db_engine, enable_commenter=True)

    session_maker = sessionmaker(db_engine, expire_on_commit=False, autoflush=True)
    flask_scoped_session(session_maker, app=app)

    atexit.register(dbc.close)

    @app.get("/health")
    def health():
        return "", 204

    storage_client = GoogleCloudStorage()

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
