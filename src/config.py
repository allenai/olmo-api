import json
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Self

from flask import g
from werkzeug.local import LocalProxy


@dataclass
class Database:
    conninfo: str
    min_size: int = 1
    max_size: int = 2


class ModelType(StrEnum):
    Base = "base"  # base models, that behave like autocomplete
    Chat = "chat"  # chat models, that have been fine-tuned for conversation


@dataclass
class Model:
    id: str
    name: str
    description: str
    compute_source_id: str
    model_type: ModelType


@dataclass
class BaseInferenceEngineConfig:
    token: str
    # The default id in the `available_models` list below.
    default_model: str
    available_models: list[Model]


@dataclass
class InferD(BaseInferenceEngineConfig):
    address: str


@dataclass
class Server:
    num_proxies: int
    log_level: str
    admins: list[str]
    api_origin: str
    ui_origin: str
    # Origins (http://<host>:<port>) that we're allowed to redirect clients to after authentication.
    # The ui_origin is automatically included.
    allowed_redirects: list[str]


DEFAULT_CONFIG_PATH = "/secret/cfg/config.json"


@dataclass
class Config:
    db: Database
    inferd: InferD
    server: Server
    togetherai: BaseInferenceEngineConfig

    @classmethod
    def load(cls, path: str = DEFAULT_CONFIG_PATH) -> Self:
        with open(path) as f:
            data = json.load(f)
            return cls(
                db=Database(**data["db"]),
                inferd=InferD(
                    address=data["inferd"]["address"],
                    token=data["inferd"]["token"],
                    default_model=data["inferd"]["default_model"],
                    available_models=[
                        Model(**m) for m in data["inferd"]["available_models"]
                    ],
                ),
                server=Server(
                    data["server"]["num_proxies"],
                    data["server"].get("log_level", "INFO"),
                    data["server"].get("admins", []),
                    data["server"].get("origin", "http://localhost:8000"),
                    data["server"].get("ui_origin", "http://localhost:8080"),
                    data["server"].get("allowed_redirects", []),
                ),
                togetherai=BaseInferenceEngineConfig(
                    token=data["togetherai"].get("token"),
                    default_model=data["togetherai"].get("default_model"),
                    available_models=[
                        Model(**m) for m in data["togetherai"]["available_models"]
                    ],
                ),
            )


def get_config() -> Config:
    if "cfg" not in g:
        g.cfg = Config.load(os.environ.get("FLASK_CONFIG_PATH", DEFAULT_CONFIG_PATH))

    return g.cfg


cfg: Config = LocalProxy(get_config)  # type: ignore - this is a LocalProxy of a Config. We're forcing it to be a Config here so other modules don't have any trouble using it


def get_available_models() -> Iterable[Model]:
    if "available_models" not in g:
        g.available_models = cfg.togetherai.available_models

    return g.available_models


available_models: Iterable[Model] = LocalProxy(get_available_models)  # type: ignore - this is a LocalProxy of a list. We're forcing it to be a list here so other modules don't have any trouble using it
