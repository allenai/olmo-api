from typing import Self

from pydantic import BaseModel, Field, ModelWrapValidatorHandler, SecretStr, model_validator
from pydantic.functional_validators import field_validator
from pydantic_settings import BaseSettings, JsonConfigSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict

DEFAULT_CONFIG_PATH = "./config.json"

class Database(BaseModel):
    conninfo: str
    min_size: int = Field(default=1)
    max_size: int = Field(default=2)

class SQLAlachemy(BaseModel):
    pool_size: int  # default 3?
    max_overflow: int  # default 3?

class BaseInferenceEngineConfig(BaseModel):
    token: str


class InferD(BaseInferenceEngineConfig):
    address: str


class Modal(BaseInferenceEngineConfig):
    token_secret: str


class CirrascaleBackend(BaseModel):
    # The base_url should not contain the port.
    base_url: str
    api_key: str


class Cirrascale(BaseModel):
    base_url: str
    api_key: SecretStr


class Ai2ModelHub(BaseModel):
    base_url: str
    api_key: SecretStr


class Server(BaseModel):
    num_proxies: int
    log_level: str = Field(default="INFO")
    admins: list[str] = Field(default=[])
    api_origin: str = Field(alias="origin", default="http://localhost:8000")
    ui_origin: str = Field(default="http://localhost:8000")
    # Origins (http://<host>:<port>) that we're allowed to redirect clients to after authentication.
    # The ui_origin is automatically included.
    allowed_redirects: list[str] = Field(default=[])


class Auth(BaseModel):
    domain: str = Field(alias="auth0_domain")
    audience: str = Field(alias="auth0_audience")


class Wildguard(BaseModel):
    address: str
    token: str
    compute_source_id: str



class InfiniGramSource(BaseModel):
    name: str
    usage: str
    display_name: str | None
    url: str | None
    secondary_name: str | None

    @model_validator(mode="wrap")
    @classmethod
    def generate_initial_values(cls, data: dict, handler: ModelWrapValidatorHandler[Self]):
        initial_values = {
            "name": data.get("name"),
            "usage": data.get("usage"),
            "display_name": data.get("display_name") or data.get("name"),
            "url": data.get("url") or f"https://huggingface.co/datasets/allenai/{data.get('name')}",
            "secondary_name": data.get("secondary_name"),
        }

        validated_values = handler(initial_values)

        return validated_values


class InfiniGram(BaseModel):
    api_url: str = Field(default="https://infinigram-api.allen.ai")
    model_index_map: dict[str, str] = Field(default_factory=lambda: {
                        "OLMo-2-1124-13B-Instruct": "olmo-2-1124-13b",
                        "olmoe-0125": "olmoe-0125-1b-7b",
                        "olmo-2-0325-32b-instruct": "olmo-2-0325-32b",
                        "tulu-3-1-8b": "tulu-3-8b",
                        "Llama-3-1-Tulu-3-70B": "tulu-3-70b",
                        "tulu3-405b": "tulu-3-405b",
                        "cs-OLMo-2-1124-13B-Instruct": "olmo-2-1124-13b",
                        "cs-OLMo-2-0325-32B-Instruct": "olmo-2-0325-32b",
                        "cs-Llama-3.1-Tulu-3.1-8B": "tulu-3-8b",
                        "cs-Llama-3.1-Tulu-3-70B": "tulu-3-70b",
                    })
    source_map: dict[str, InfiniGramSource] = Field(alias="sources")

    @field_validator("sources", mode="before", check_fields=False)
    @classmethod
    def map_infinigram_sources(cls, infinigram_sources: list[dict]) -> dict[str, InfiniGramSource]:
        source_dict = {}
        for item in infinigram_sources or []:
            validated_source = InfiniGramSource.model_validate(item)
            source_dict[validated_source.name] = validated_source

        return source_dict


class Hubspot(BaseModel):
    token: str


class GoogleCloudServices(BaseModel):
    api_key: str
    storage_bucket: str
    recaptcha_key: str
    enable_recaptcha: bool
    require_recaptcha: bool
    safety_storage_bucket: str


class FeatureFlags(BaseModel):
    allow_files_only_model_in_thread: bool = False
    show_internal_tools: bool = False
    enable_blocking_video_safety_check: bool = False
    enable_queued_video_safety_check: bool = True


class Beaker(BaseModel):
    address: str
    user_token: str


class ModalOpenAI(BaseModel):
    api_key: SecretStr


class McpServer(BaseModel):
    url: str
    headers: dict[str, str]
    name: str
    id: str
    enabled: bool
    available_for_all_models: bool


class Mcp(BaseModel):
    servers: list[McpServer]


class Otel(BaseModel):
    collector_type: str


class GoogleModerateText(BaseModel):
    default_confidence_threshold: float = Field(default=0.8)
    default_severity_threshold: float = Field(default=0.7)
    default_unsafe_violation_categories: list[str] = Field(
        default_factory=lambda: [
            "Toxic",
            "Derogatory",
            "Violent",
            "Sexual",
            "Insult",
            "Profanity",
            "Death, Harm & Tragedy",
            "Firearms & Weapons",
            "Public Safety",
            "War & Conflict",
            "Dangerous Content",
        ]
    )

class JsonSettings(BaseSettings):
    model_config = SettingsConfigDict(json_file=DEFAULT_CONFIG_PATH)

    db: Database
    sql_alchemy: SQLAlachemy
    inferd: InferD
    server: Server
    modal: Modal
    auth: Auth
    wildguard: Wildguard
    infini_gram: InfiniGram
    hubspot: Hubspot
    google_cloud_services: GoogleCloudServices
    feature_flags: FeatureFlags
    beaker: Beaker
    cirrascale_backend: CirrascaleBackend
    cirrascale: Cirrascale
    ai2_model_hub: Ai2ModelHub
    modal_openai: ModalOpenAI
    mcp: Mcp
    google_moderate_text: GoogleModerateText = Field(alias="google_safety_check", default_factory=GoogleModerateText)
    otel: Otel
    queue_url: str
    models: list[dict]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        env_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        file_secret_settings: PydanticBaseSettingsSource,  # noqa: ARG003
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (JsonConfigSettingsSource(settings_cls),)

settings = JsonSettings()  # pyright: ignore[reportCallIssue]
