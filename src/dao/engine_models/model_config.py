from datetime import datetime
from enum import StrEnum

from sqlalchemy import ARRAY, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.config.ModelConfig import FileRequiredToPromptOption, ModelHost, ModelType

from .base import Base


class PromptType(StrEnum):
    TEXT_ONLY = "text_only"
    MULTI_MODAL = "multi_modal"


class ModelConfig(Base, kw_only=True):
    __tablename__ = "model_config"

    id: Mapped[str] = mapped_column(primary_key=True)
    host: Mapped[ModelHost]
    name: Mapped[str]
    description: Mapped[str]
    # We already have a model_type enum in the DB but it's hard to change through alembic so this makes a new one
    model_type: Mapped[ModelType]
    model_id_on_host: Mapped[str]
    internal: Mapped[bool]
    prompt_type: Mapped[PromptType]
    order: Mapped[int]
    default_system_prompt: Mapped[str | None] = mapped_column(default=None)
    family_id: Mapped[str | None] = mapped_column(default=None)
    family_name: Mapped[str | None] = mapped_column(default=None)

    available_time: Mapped[datetime | None] = mapped_column(default=None)
    deprecation_time: Mapped[datetime | None] = mapped_column(default=None)

    created_time: Mapped[datetime] = mapped_column(
        server_default=func.now(), init=False
    )
    updated_time: Mapped[datetime] = mapped_column(
        server_onupdate=func.now(), init=False
    )

    __mapper_args__ = {
        "polymorphic_identity": PromptType.TEXT_ONLY,
        "polymorphic_on": "prompt_type",
    }


class MultiModalModelConfig(ModelConfig, kw_only=True):
    __tablename__ = "multi_modal_model_config"

    id: Mapped[str] = mapped_column(ForeignKey("model_config.id"), primary_key=True)
    accepted_file_types: Mapped[list[str]] = mapped_column(ARRAY(String))
    max_files_per_message: Mapped[int | None] = mapped_column(default=None)
    require_file_to_prompt: Mapped[FileRequiredToPromptOption | None] = mapped_column(
        default=None
    )
    max_total_file_size: Mapped[int | None] = mapped_column(default=None)
    allow_files_in_followups: Mapped[bool | None]

    __mapper_args__ = {"polymorphic_identity": PromptType.MULTI_MODAL}
