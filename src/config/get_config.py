import os
from functools import cache
from typing import cast

from werkzeug.local import LocalProxy

from src.config.Config import DEFAULT_CONFIG_PATH, Config


@cache
def get_config():
    return Config.load(path=os.environ.get("FLASK_CONFIG_PATH", default=DEFAULT_CONFIG_PATH))


get_config = cast(Config, LocalProxy(get_config))
