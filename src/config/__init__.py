import os
from typing import Optional

from werkzeug.local import LocalProxy

from src.config.Config import DEFAULT_CONFIG_PATH, Config

_config: Optional[Config] = None


def get_config():
    global _config
    if _config is None:
        _config = Config.load(
            path=os.environ.get("FLASK_CONFIG_PATH", default=DEFAULT_CONFIG_PATH)
        )

    return _config


cfg = LocalProxy(get_config)
