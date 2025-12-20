import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ARRAY,
    DateTime,
    PrimaryKeyConstraint,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src import obj
from src.dao.engine_models.model_config import ModelType

from .base import Base

if TYPE_CHECKING:
    from src.dao.engine_models.message import Message
    from src.dao.engine_models.tool_definitions import ToolDefinition


class PromptTemplate(Base, kw_only=True):
    __tablename__ = "prompt_template"
    __table_args__ = (PrimaryKeyConstraint("id", name="prompt_template_pkey"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True, default_factory=obj.new_id_generator("p_tpl"))
    name: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    creator: Mapped[str]
    created: Mapped[datetime.datetime] = mapped_column(server_default=text("now()"))
    updated: Mapped[datetime.datetime] = mapped_column(server_default=text("now()"))
    deleted: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))

    opts: Mapped[dict]
    model_type: Mapped[ModelType]
    file_urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True, default=None)
    tool_definitions: Mapped[list["ToolDefinition"] | None] = relationship(
        "ToolDefinition",
        secondary="prompt_template_tool_definition_association",
        back_populates="prompt_templates",
        default_factory=list,
    )

    # NOTE: JSONB changes aren't tracked by SQLAlchemy automatically
    extra_parameters: Mapped[dict[str, Any] | None] = mapped_column(nullable=True, default=None)

    messages: Mapped[list["Message"]] = relationship("Message", back_populates="prompt_template")
