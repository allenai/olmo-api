import datetime
from typing import Any, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.object_id import new_id_generator
from db.models.base import Base
from db.models.completion import Completion
from db.models.input_parts import InputPart
from db.models.label import Label
from db.models.prompt_template import PromptTemplate
from db.models.pydantic_type import PydanticType
from db.models.tool_call import ToolCall
from db.models.tool_definitions import ToolDefinition


# Generated using sqlacodegen
class Message(Base, kw_only=True):
    __tablename__ = "message"
    __table_args__ = (
        ForeignKeyConstraint(
            ["completion"],
            ["completion.id"],
            ondelete="CASCADE",
            name="message_completion_fkey",
        ),
        ForeignKeyConstraint(
            ["original"],
            ["message.id"],
            ondelete="CASCADE",
            name="message_original_fkey",
        ),
        ForeignKeyConstraint(["parent"], ["message.id"], ondelete="CASCADE", name="message_parent_fkey"),
        ForeignKeyConstraint(["root"], ["message.id"], ondelete="CASCADE", name="message_root_fkey"),
        ForeignKeyConstraint(["template"], ["prompt_template.id"], name="message_template_fkey"),
        PrimaryKeyConstraint("id", name="message_pkey"),
        Index("message_created_ix", "created"),
        Index("message_creator_ix", "creator"),
        Index("message_original_fkey_ix", "original"),
        Index("message_parent_fkey_ix", "parent"),
        Index("message_root_fkey_ix", "root"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True, default_factory=new_id_generator("msg"))
    content: Mapped[str] = mapped_column(Text, nullable=False)

    input_parts: Mapped[list[InputPart] | None] = mapped_column(
        ARRAY(PydanticType(InputPart)), nullable=True, default=None
    )

    creator: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    opts: Mapped[dict] = mapped_column(JSONB, nullable=False)
    root: Mapped[str] = mapped_column(Text, nullable=False)
    created: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), nullable=False, server_default=text("now()"), init=False
    )
    final: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)
    private: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    model_host: Mapped[str] = mapped_column(Text, nullable=False)
    agent_id: Mapped[str | None] = mapped_column(default=None)
    deleted: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), default=None)
    parent: Mapped[Optional[str]] = mapped_column(Text)
    template: Mapped[Optional[str]] = mapped_column(Text, default=None)
    logprobs: Mapped[Optional[list[list[dict]]]] = mapped_column(ARRAY(JSONB()), default=None)
    completion: Mapped[Optional[str]] = mapped_column(Text, default=None)
    original: Mapped[Optional[str]] = mapped_column(Text, default=None)
    model_type: Mapped[Optional[str]] = mapped_column(
        Enum("base", "chat", "image_prompt", name="model_type"), default=None
    )
    finish_reason: Mapped[Optional[str]] = mapped_column(Text, default=None)
    harmful: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    expiration_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    file_urls: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text()), nullable=True, default=None)

    thinking: Mapped[str | None] = mapped_column(default=None)

    tool_definitions: Mapped[list[ToolDefinition] | None] = relationship(
        "ToolDefinition",
        secondary="message_tool_definition_association",
        back_populates="messages",
        default_factory=list,
    )

    tool_calls: Mapped[list[ToolCall] | None] = relationship(
        "ToolCall",
        back_populates="message",
        default_factory=list,
        cascade="all, delete",
    )

    error_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    error_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    error_severity: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

    # NOTE: JSONB changes aren't tracked by SQLAlchemy automatically
    extra_parameters: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=None)

    completion_: Mapped[Completion | None] = relationship("Completion", back_populates="message", init=False)

    children: Mapped[list["Message"] | None] = relationship(back_populates="parent_", foreign_keys=[parent], init=False)
    parent_: Mapped[Optional["Message"]] = relationship(
        back_populates="children", remote_side=[id], foreign_keys=[parent], init=False
    )

    prompt_template: Mapped[PromptTemplate | None] = relationship(
        "PromptTemplate", back_populates="messages", init=False
    )
    labels: Mapped[list[Label]] = relationship(
        "Label",
        back_populates="message_",
        init=False,
        cascade="all, delete",
    )
