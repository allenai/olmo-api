import json
import os
from dataclasses import dataclass
from typing import Self

from src.config.Model import Model, MultiModalModel, map_model_from_config


@dataclass
class Database:
    conninfo: str
    min_size: int = 1
    max_size: int = 2


@dataclass
class BaseInferenceEngineConfig:
    token: str


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


@dataclass
class Hubspot:
    token: str


@dataclass
class GoogleCloudServices:
    api_key: str
    storage_bucket: str
    recaptcha_key: str


DEFAULT_CONFIG_PATH = "/secret/cfg/config.json"


@dataclass
class Config:
    db: Database
    inferd: InferD
    server: Server
    modal: Modal
    auth: Auth
    wildguard: Wildguard
    infini_gram: InfiniGram
    hubspot: Hubspot
    google_cloud_services: GoogleCloudServices
    models: list[Model | MultiModalModel]

    @classmethod
    def load(cls, path: str = DEFAULT_CONFIG_PATH) -> Self:
        with open(path, encoding="locale") as f:
            data = json.load(f)
            return cls(
                db=Database(**data["db"]),
                inferd=InferD(
                    address=data["inferd"]["address"],
                    token=data["inferd"]["token"],
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
                        "OLMo-peteish-dpo-preview": "olmoe",
                        "OLMoE-1B-7B-0924-Instruct": "olmoe",
                        "OLMo-2-1124-13B-Instruct": "olmo-2-1124-13b",
                        "olmoe-0125": "olmo-2-1124-13b",
                        # TODO: point to the newest index once we add more training data
                        "olmo-2-0325-32b-instruct": "olmo-2-1124-13b",
                    },
                    api_url="https://infinigram-api.allen.ai",
                    # api_url="http://host.docker.internal:8008",
                ),
                hubspot=Hubspot(token=data["hubspot"]["token"]),
                google_cloud_services=GoogleCloudServices(
                    api_key=data["google_cloud_services"]["api_key"],
                    storage_bucket=data["google_cloud_services"]["storage_bucket"],
                    # Getting the recaptcha key from env lets us use a separate key for dev work
                    recaptcha_key=os.getenv(
                        "RECAPTCHA_KEY",
                        data["google_cloud_services"].get("recaptcha_key"),
                    ),
                ),
                models=[map_model_from_config(model_config) for model_config in data["models"]],
            )
