from datetime import datetime
from enum import StrEnum

from sqlalchemy import ARRAY, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.config.ModelConfig import FileRequiredToPromptOption, ModelHost, ModelType

from .base import Base


class PromptType(StrEnum):
    text_only = "text_only"
    multi_modal = "multi_modal"


class ModelConfig(Base):
    __tablename__ = "model_config"

    id: Mapped[str] = mapped_column(primary_key=True, init=False)
    host: Mapped[ModelHost]
    name: Mapped[str]
    description: Mapped[str]
    # We already have a model_type enum in the DB but it's hard to change through alembic so this makes a new one
    model_type: Mapped[ModelType]
    model_id_on_host: Mapped[str]
    default_system_prompt: Mapped[str | None]
    family_id: Mapped[str | None]
    family_name: Mapped[str | None]
    internal: Mapped[bool]
    prompt_type: Mapped[PromptType]
    order: Mapped[int]

    available_time: Mapped[datetime | None]
    deprecation_time: Mapped[datetime | None]

    __mapper_args__ = {
        "polymorphic_identity": "model_config",
        "polymorphic_on": "prompt_type",
    }


class MultiModalModelConfig(ModelConfig):
    __tablename__ = "multi_model_model_config"

    id: Mapped[str] = mapped_column(ForeignKey("model_config.id"), primary_key=True, init=False)
    accepted_file_types: Mapped[list[str]] = mapped_column(ARRAY(String))
    max_files_per_message: Mapped[int | None]
    require_file_to_prompt: Mapped[FileRequiredToPromptOption | None]
    max_total_file_size: Mapped[int | None]
    allow_files_in_followups: Mapped[bool | None]

    __mapper_args__ = {"polymorphic_identity": "multi_model_model_config"}
