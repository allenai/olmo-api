import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src import obj

if TYPE_CHECKING:
    from db.models.message import Message
    from db.models.prompt_template import PromptTemplate

from .base import Base


class ToolSource(StrEnum):
    # where did this tool come from
    INTERNAL = "internal"
    USER_DEFINED = "user_defined"
    MCP = "model_context_protocol"


# Association table for many-to-many relationship
class MessageToolDefinition(Base, kw_only=True):
    __tablename__ = "message_tool_definition_association"

    message_id: Mapped[str] = mapped_column(Text, ForeignKey("message.id", ondelete="CASCADE"), primary_key=True)
    tool_definition_id: Mapped[str] = mapped_column(
        Text, ForeignKey("tool_definition.id", ondelete="CASCADE"), primary_key=True
    )

    created: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), nullable=False, server_default=text("now()"), init=False
    )


class PromptTemplateToolDefinition(Base, kw_only=True):
    __tablename__ = "prompt_template_tool_definition_association"

    prompt_template_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(column="prompt_template.id", ondelete="CASCADE"),
        primary_key=True,
    )

    tool_definition_id: Mapped[str] = mapped_column(
        Text, ForeignKey("tool_definition.id", ondelete="CASCADE"), primary_key=True
    )

    created: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), nullable=False, server_default=text("now()"), init=False
    )


class ToolDefinition(Base, kw_only=True):
    __tablename__ = "tool_definition"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default_factory=obj.new_id_generator("td"))

    name: Mapped[str]
    description: Mapped[str]

    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    tool_source: Mapped[ToolSource] = mapped_column(Enum(ToolSource), nullable=False)

    mcp_server_id: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    created: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), nullable=False, server_default=text("now()"), init=False
    )

    messages: Mapped[list["Message"] | None] = relationship(
        "Message",
        back_populates="tool_definitions",
        secondary="message_tool_definition_association",
        default_factory=list,
        passive_deletes=True,
    )

    prompt_templates: Mapped[list["PromptTemplate"] | None] = relationship(
        "PromptTemplate",
        back_populates="tool_definitions",
        secondary="prompt_template_tool_definition_association",
        default_factory=list,
        passive_deletes=True,
    )
