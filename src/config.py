import datetime
import json
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Self, TypedDict, Unpack, cast


@dataclass
class Database:
    conninfo: str
    min_size: int = 1
    max_size: int = 2


class ModelType(StrEnum):
    Base = "base"  # base models, that behave like autocomplete
    Chat = "chat"  # chat models, that have been fine-tuned for conversation


class ModelConfig(TypedDict):
    id: str
    name: str
    description: str
    compute_source_id: str
    model_type: ModelType
    is_deprecated: Optional[bool]
    system_prompt: Optional[str]
    family_id: Optional[str]
    family_name: Optional[str]
    available_time: Optional[str]
    deprecation_time: Optional[str]


@dataclass
class Model:
    id: str
    name: str
    description: str
    compute_source_id: str
    model_type: ModelType
    available_time: datetime.datetime
    system_prompt: Optional[str] = None
    family_id: Optional[str] = None
    family_name: Optional[str] = None
    deprecation_time: Optional[datetime.datetime] = None

    @staticmethod
    def from_config(
        **kwargs: Unpack[ModelConfig],
    ):
        available_time = kwargs.get("available_time")
        mapped_available_time = (
            datetime.datetime.fromisoformat(available_time)
            if available_time is not None
            else datetime.datetime.min
        )

        deprecation_time = kwargs.get("deprecation_time")
        mapped_deprecation_time = (
            datetime.datetime.min
            if kwargs.get("is_deprecated") is True
            else datetime.datetime.fromisoformat(deprecation_time)
            if deprecation_time is not None
            else None
        )

        return Model(
            id=cast(str, kwargs.get("id")),
            name=cast(str, kwargs.get("name")),
            description=cast(str, kwargs.get("description")),
            compute_source_id=cast(str, kwargs.get("compute_source_id")),
            model_type=cast(ModelType, kwargs.get("model_type")),
            system_prompt=kwargs.get("system_prompt"),
            family_id=kwargs.get("family_id"),
            family_name=kwargs.get("family_name"),
            available_time=mapped_available_time,
            deprecation_time=mapped_deprecation_time,
        )


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


@dataclass
class Hubspot:
    token: str


@dataclass
class GoogleCloudServices:
    api_key: str
    storage_bucket: str


DEFAULT_CONFIG_PATH = "/secret/cfg/config.json"


@dataclass
class Config:
    db: Database
    inferd: InferD
    server: Server
    modal: BaseInferenceEngineConfig
    auth: Auth
    wildguard: Wildguard
    infini_gram: InfiniGram
    hubspot: Hubspot
    google_cloud_services: GoogleCloudServices

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
                        Model.from_config(**m)
                        for m in data["inferd"]["available_models"]
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
                        Model.from_config(**m)
                        for m in data["modal"]["available_models"]
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
                        "OLMo-peteish-dpo-preview": "olmoe",
                        "OLMoE-1B-7B-0924-Instruct": "olmoe",
                        "OLMo-2-1124-13B-Instruct": "olmo-2-1124-13b",
                        "olmoe-0125": "olmo-2-1124-13b",
                    },
                    api_url="https://infinigram-api.allen.ai",
                    # api_url="http://host.docker.internal:8008",
                ),
                hubspot=Hubspot(token=data["hubspot"]["token"]),
                google_cloud_services=GoogleCloudServices(
                    api_key=data["google_cloud_services"]["api_key"],
                    storage_bucket=data["google_cloud_services"]["storage_bucket"],
                ),
            )


cfg = Config.load(path=os.environ.get("FLASK_CONFIG_PATH", default=DEFAULT_CONFIG_PATH))

model_hosts = ["inferd", "modal"]
