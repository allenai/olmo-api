import atexit
import logging
import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from src import config, db, error, util, v3
from src.dao import paged


def create_app():
    app = Flask(__name__)

    # Use ISO formatted datetimes
    app.json = util.CustomJSONProvider(app)

    cfg = config.Config.load(
        os.environ.get("FLASK_CONFIG_PATH", config.DEFAULT_CONFIG_PATH)
    )

    dbc = db.Client.from_config(cfg.db)
    atexit.register(dbc.close)

    @app.get("/health")
    def health():
        try:
            # These checks will keep a new pod from starting if something's wrong with the schema
            dbc.message.get_list(opts=paged.Opts(limit=1))
            dbc.template.prompts()
            dbc.label.get_list(opts=paged.Opts(limit=1))
        except Exception as e:
            logging.getLogger().error(
                f"Exception occurred on application startup: {repr(e)}"
            )
            return repr(e), 500

        return "", 204

    app.register_blueprint(v3.Server(dbc), url_prefix="/v3", name="v3")
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
