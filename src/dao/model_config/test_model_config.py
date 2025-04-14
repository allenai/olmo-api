from enum import StrEnum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import MetaData
from sqlalchemy.orm import Mapped, mapped_column

from src.dao.base import Base


class PromptType(StrEnum):
    text_only = "text_only"
    multi_modal = "multi_modal"


class TestModelConfig(Base):
    __tablename__ = "test_model_config"

    id: Mapped[str] = mapped_column(primary_key=True)
    prompt_type: Mapped[PromptType] = mapped_column(SqlEnum(PromptType, metadata=MetaData(schema="model_config")))

    def __repr__(self) -> str:
        return f"TestModelConfig(id={self.id!r}, prompt_type={self.prompt_type!r})"
