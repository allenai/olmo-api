import atexit
import logging
import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from src import db, error, util, v3
from src.config import get_config
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.v4 import create_v4_blueprint


def create_app():
    app = Flask(__name__)

    # Use ISO formatted datetimes
    app.json = util.CustomJSONProvider(app)

    cfg = get_config.Config.load(os.environ.get("FLASK_CONFIG_PATH", get_config.DEFAULT_CONFIG_PATH))

    dbc = db.Client.from_config(cfg.db)
    atexit.register(dbc.close)

    @app.get("/health")
    def health():
        return "", 204

    storage_client = GoogleCloudStorage(bucket_name=cfg.google_cloud_services.storage_bucket)

    app.register_blueprint(v3.Server(dbc, storage_client), url_prefix="/v3", name="v3")
    app.register_blueprint(
        create_v4_blueprint(dbc=dbc, storage_client=storage_client),
        url_prefix="/v4",
        name="v4",
    )
    app.register_error_handler(Exception, error.handle)

    if not app.debug:
        h = logging.StreamHandler()
        h.setFormatter(util.StackdriverJsonFormatter())
        logging.basicConfig(level=cfg.server.log_level, handlers=[h])

    return ProxyFix(
        app,
        x_for=cfg.server.num_proxies,
        x_proto=cfg.server.num_proxies,
        x_host=cfg.server.num_proxies,
        x_port=cfg.server.num_proxies,
    )


app = create_app()
