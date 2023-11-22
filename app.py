from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from inferd.msg.inferd_pb2_grpc import InferDStub
from src import util, db, error, v3, config

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

    channel = grpc.secure_channel(cfg.inferd.address, grpc.ssl_channel_credentials())
    atexit.register(channel.close)
    inferd = InferDStub(channel)

    @app.get("/health")
    def health(): # pyright: ignore
        return "", 204

    app.register_blueprint(v3.Server(dbc, inferd, cfg), url_prefix="/v3", name="v3")
    app.register_error_handler(Exception, error.handle)

    ProxyFix(app, x_for=cfg.server.num_proxies, x_proto=cfg.server.num_proxies,
             x_host=cfg.server.num_proxies, x_port=cfg.server.num_proxies)

    if not app.debug:
        h = logging.StreamHandler()
        h.setFormatter(util.StackdriverJsonFormatter())
        logging.basicConfig(level=cfg.server.log_level, handlers=[h])

    return app

app = create_app()

