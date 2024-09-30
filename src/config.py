import json
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Self


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
    is_deprecated: Optional[bool] = None


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
class Modal(BaseInferenceEngineConfig):
    token_secret: str


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


@dataclass
class Auth:
    domain: str
    audience: str


@dataclass
class Wildguard:
    address: str
    token: str
    compute_source_id: str


@dataclass
class InfiniGram:
    api_url: str
    model_index_map: dict[str, str]


DEFAULT_CONFIG_PATH = "/secret/cfg/config.json"


@dataclass
class Config:
    db: Database
    inferd: InferD
    server: Server
    togetherai: BaseInferenceEngineConfig
    modal: BaseInferenceEngineConfig
    auth: Auth
    wildguard: Wildguard
    infini_gram: InfiniGram

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
                modal=Modal(
                    token=data["modal"].get("token"),
                    token_secret=data["modal"].get("token_secret"),
                    default_model=data["modal"].get("default_model"),
                    available_models=[
                        Model(**m) for m in data["modal"]["available_models"]
                    ],
                ),
                togetherai=BaseInferenceEngineConfig(
                    token=data["togetherai"].get("token"),
                    default_model=data["togetherai"].get("default_model"),
                    available_models=[
                        Model(**m) for m in data["togetherai"]["available_models"]
                    ],
                ),
                auth=Auth(
                    domain=data["auth"].get("auth0_domain"),
                    audience=data["auth"].get("auth0_audience"),
                ),
                wildguard=Wildguard(
                    address=data["wildguard"].get("address"),
                    token=data["wildguard"].get("token"),
                    compute_source_id=data["wildguard"].get("compute_source_id"),
                ),
                infini_gram=InfiniGram(
                    model_index_map={
                        "olmo-7b-base": "dolma-1_7",
                        "olmo-7b-chat": "dolma-1_7",
                        "OLMo-peteish-dpo-preview": "olmoe-mix-0924",
                        "OLMoE-1B-7B-0924-Instruct": "olmoe-mix-0924",
                    },
                    api_url="https://infinigram-api.allen.ai",
                ),
            )


cfg = Config.load(path=os.environ.get("FLASK_CONFIG_PATH", default=DEFAULT_CONFIG_PATH))

model_hosts = ["togetherai", "inferd", "modal"]
