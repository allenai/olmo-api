from enum import StrEnum

from sqlalchemy.orm import Mapped, mapped_column

from src.config.ModelConfig import ModelHost, ModelType

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
    # We already have a model_type enum in the DB but it's hard to change so we're making a new one
    model_type: Mapped[ModelType] = mapped_column()
    model_id_on_host: Mapped[str]
    default_system_prompt: Mapped[str | None]
    family_id: Mapped[str | None]
    family_name: Mapped[str | None]
    internal: Mapped[bool]
    prompt_type: Mapped[PromptType]
