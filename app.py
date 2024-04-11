import atexit
import logging

import grpc
from flask import Flask
from inferd.msg.inferd_pb2_grpc import InferDStub
from werkzeug.middleware.proxy_fix import ProxyFix

from src import config, db, error, util, v3
from src.inference.InferDEngine import InferDEngine


def create_app():
    app = Flask(__name__)

    # Use ISO formatted datetimes
    app.json = util.CustomJSONProvider(app)

    cfg = config.Config.load("config.json")

    dbc = db.Client.from_config(cfg.db)
    atexit.register(dbc.close)

    channel = grpc.secure_channel(cfg.inferd.address, grpc.ssl_channel_credentials())
    atexit.register(channel.close)
    inferd = InferDStub(channel)
    inference_engine = InferDEngine(cfg)

    @app.get("/health")
    def health():  # pyright: ignore
        return "", 204

    app.register_blueprint(
        v3.Server(dbc, inference_engine, cfg), url_prefix="/v3", name="v3"
    )
    app.register_error_handler(Exception, error.handle)

    ProxyFix(
        app,
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
