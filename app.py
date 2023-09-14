from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from inferd.msg.inferd_pb2_grpc import InferDStub
from src import util, db, error, v2, config

import os
import logging
import atexit
import grpc

def create_app():
    app = Flask(__name__)

    # Use ISO formatted datetimes
    app.json = util.CustomJSONProvider(app)

    cfg = config.Config.load()

    dbc = db.Client.from_config(cfg.db)
    atexit.register(dbc.close)

    channel = grpc.insecure_channel(cfg.inferd.address)
    atexit.register(channel.close)
    inferd = InferDStub(channel)

    @app.get("/health")
    def health(): # pyright: ignoreUnusedFunction
        return "", 204

    app.register_blueprint(v2.Server(dbc, inferd), url_prefix="/v2", name="v2")
    app.register_error_handler(HTTPException, error.handle)

    ProxyFix(app, x_for=cfg.server.num_proxies, x_proto=cfg.server.num_proxies,
             x_host=cfg.server.num_proxies, x_port=cfg.server.num_proxies)

    if not app.debug:
        h = logging.StreamHandler()
        h.setFormatter(util.StackdriverJsonFormatter())
        logging.basicConfig(level=cfg.log_level, handlers=[h])

    return app

app = create_app()

