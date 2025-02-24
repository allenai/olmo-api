from enum import StrEnum
from typing import Optional, TypedDict


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
    system_prompt: Optional[str]
    family_id: Optional[str]
    family_name: Optional[str]
    available_time: Optional[str]
    deprecation_time: Optional[str]


class FileRequiredToPromptOption(StrEnum):
    FirstMessage = "first_message"
    AllMessages = "all_messages"
    NoRequirement = "no_requirement"


class MultiModalModelConfig(ModelConfig):
    accepts_files: Optional[bool]
    accepted_file_types: list[str]
    max_files_per_message: Optional[int]
    require_file_to_prompt: Optional[FileRequiredToPromptOption]
    max_total_file_size: Optional[int]
    allow_files_in_followups: Optional[bool]
