import os
from functools import cache
from typing import cast

from werkzeug.local import LocalProxy

# we're re-exporting everything from config
from src.config.Config import *  # noqa: F403
from src.config.Config import DEFAULT_CONFIG_PATH, Config


@cache
def get_config():
    return Config.load(path=os.environ.get("FLASK_CONFIG_PATH", default=DEFAULT_CONFIG_PATH))


cfg = cast(Config, LocalProxy(get_config))
