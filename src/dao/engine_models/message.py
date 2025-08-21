import datetime
from typing import Optional

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

from src import obj
from src.dao.engine_models.completion import Completion
from src.dao.engine_models.label import Label
from src.dao.engine_models.prompt_template import PromptTemplate
from src.dao.engine_models.tool_call import ToolCall

from .base import Base


# Generated using sqlacodegen
class Message(Base, kw_only=True):
    __tablename__ = "message"
    __table_args__ = (
        ForeignKeyConstraint(["completion"], ["completion.id"], ondelete="CASCADE", name="message_completion_fkey"),
        ForeignKeyConstraint(["original"], ["message.id"], ondelete="CASCADE", name="message_original_fkey"),
        ForeignKeyConstraint(["parent"], ["message.id"], ondelete="CASCADE", name="message_parent_fkey"),
        ForeignKeyConstraint(["root"], ["message.id"], ondelete="CASCADE", name="message_root_fkey"),
        ForeignKeyConstraint(["template"], ["prompt_template.id"], name="message_template_fkey"),
        PrimaryKeyConstraint("id", name="message_pkey"),
        Index("message_created_ix", "created"),
        Index("message_original_fkey_ix", "original"),
        Index("message_parent_fkey_ix", "parent"),
        Index("message_root_fkey_ix", "root"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True, default_factory=obj.new_id_generator("msg"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
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

    tool_calls: Mapped[list[ToolCall] | None] = relationship(
        back_populates="message", cascade="all, delete", lazy="joined", default_factory=list
    )

    completion_: Mapped[Completion | None] = relationship("Completion", back_populates="message", init=False)

    children: Mapped[list["Message"] | None] = relationship(back_populates="parent_", foreign_keys=[parent], init=False)
    parent_: Mapped[Optional["Message"]] = relationship(
        back_populates="children", remote_side=[id], foreign_keys=[parent], init=False
    )

    prompt_template: Mapped[PromptTemplate | None] = relationship(
        "PromptTemplate", back_populates="message", init=False
    )
    labels: Mapped[list[Label]] = relationship("Label", back_populates="message_", init=False)
