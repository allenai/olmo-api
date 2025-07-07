import json
import os
from dataclasses import dataclass
from typing import Self

from src.config.InfiniGramSource import InfiniGramSource, map_infinigram_sources
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
class CirrascaleBackend:
    # The base_url should not contain the port.
    base_url: str
    api_key: str


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
    source_map: dict[str, InfiniGramSource]


@dataclass
class Hubspot:
    token: str


@dataclass
class GoogleCloudServices:
    api_key: str
    storage_bucket: str
    recaptcha_key: str
    enable_recaptcha: bool
    require_recaptcha: bool


@dataclass
class FeatureFlags:
    enable_dynamic_model_config: bool
    allow_files_only_model_in_thread: bool


@dataclass
class Beaker:
    address: str
    user_token: str


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
    feature_flags: FeatureFlags
    beaker: Beaker
    cirrascale_backend: CirrascaleBackend

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
                cirrascale_backend=CirrascaleBackend(
                    base_url=data["cirrascale_backend"]["base_url"],
                    api_key=data["cirrascale_backend"]["api_key"],
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
                        "OLMo-2-1124-13B-Instruct": "olmo-2-1124-13b",
                        "olmoe-0125": "olmoe-0125-1b-7b",
                        "olmo-2-0325-32b-instruct": "olmo-2-0325-32b",
                        "tulu-3-1-8b": "tulu-3-8b",
                        "Llama-3-1-Tulu-3-70B": "tulu-3-70b",
                        "tulu3-405b": "tulu-3-405b",
                    },
                    api_url=data["infini_gram"].get("api_url", "https://infinigram-api.allen.ai"),
                    source_map=map_infinigram_sources(data["infini_gram"].get("sources")),
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
                    enable_recaptcha=data["google_cloud_services"].get("enable_recaptcha", True),
                    require_recaptcha=data["google_cloud_services"].get("require_recaptcha", True),
                ),
                feature_flags=FeatureFlags(
                    enable_dynamic_model_config=data.get("feature_flags", {}).get("enable_dynamic_model_config", False),
                    allow_files_only_model_in_thread=data.get("feature_flags", {}).get(
                        "allow_files_only_model_in_thread", False
                    ),
                ),
                models=[map_model_from_config(model_config) for model_config in data["models"]],
                beaker=Beaker(
                    address=data.get("beaker", {}).get("address"),
                    user_token=data.get("beaker", {}).get("user_token"),
                ),
            )
