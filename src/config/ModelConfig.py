from enum import StrEnum
from typing import TypedDict


class ModelType(StrEnum):
    Base = "base"  # base models, that behave like autocomplete
    Chat = "chat"  # chat models, that have been fine-tuned for conversation


class ModelHost(StrEnum):
    InferD = "inferd"
    Modal = "modal"


class ModelConfig(TypedDict):
    id: str
    name: str
    host: ModelHost
    description: str
    compute_source_id: str
    model_type: ModelType
    internal: bool | None
    system_prompt: str | None
    family_id: str | None
    family_name: str | None
    available_time: str | None
    deprecation_time: str | None


class FileRequiredToPromptOption(StrEnum):
    FirstMessage = "first_message"
    AllMessages = "all_messages"
    NoRequirement = "no_requirement"


class MultiModalModelConfig(ModelConfig):
    accepts_files: bool | None
    accepted_file_types: list[str]
    max_files_per_message: int | None
    require_file_to_prompt: FileRequiredToPromptOption | None
    max_total_file_size: int | None
    allow_files_in_followups: bool | None
