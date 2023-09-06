from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from inferd.msg.inferd_pb2_grpc import InferDStub
from src import util, db, error, v2

import os
import logging
import atexit
import grpc

def create_app():
    app = Flask(__name__)

    # Use ISO formatted datetimes
    app.json = util.CustomJSONProvider(app)

    dbc = db.Client.from_env()
    atexit.register(dbc.close)

    channel = grpc.insecure_channel(os.getenv("INFERD_ADDR", "host.docker.internal:10000"))
    atexit.register(channel.close)
    inferd = InferDStub(channel)

    @app.get("/health")
    def health():
        return "", 204

    app.register_blueprint(v2.Server(dbc, inferd), url_prefix="/v2", name="v2")
    app.register_error_handler(HTTPException, error.handle)

    proxies = int(os.getenv("NUM_PROXIES", 1))
    ProxyFix(app, x_for=proxies, x_proto=proxies, x_host=proxies, x_port=proxies)

    if not app.debug:
        h = logging.StreamHandler()
        h.setFormatter(util.StackdriverJsonFormatter())
        lvl = os.environ.get("LOG_LEVEL", default=logging.INFO)
        logging.basicConfig(level=lvl, handlers=[h])

    return app

app = create_app()

