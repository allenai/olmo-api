from enum import StrEnum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.dao.models.base import Base


class PromptType(StrEnum):
    text_only = "text_only"
    multi_modal = "multi_modal"


class ModelConfig(Base):
    __tablename__ = "model_config"
    __table_args__ = {"schema": "model_config"}  # noqa: RUF012

    id: Mapped[str] = mapped_column(primary_key=True)
    prompt_type: Mapped[PromptType] = mapped_column(SqlEnum(PromptType, inherit_schema=True))

    def __repr__(self) -> str:
        return f"TestModelConfig(id={self.id!r}, prompt_type={self.prompt_type!r})"
