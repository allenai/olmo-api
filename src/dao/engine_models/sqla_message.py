import datetime
from typing import Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


# Generated using sqlacodegen
class Message(Base):
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

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    creator: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    opts: Mapped[dict] = mapped_column(JSONB)
    root: Mapped[str] = mapped_column(ForeignKey("message.id"))
    created: Mapped[datetime.datetime] = mapped_column(DateTime(True), server_default=text("now()"))
    final: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    private: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    model_id: Mapped[str] = mapped_column(Text)
    model_host: Mapped[str] = mapped_column(Text)
    deleted: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))
    parent: Mapped[str | None] = mapped_column(ForeignKey("message.id"))
    template: Mapped[str | None] = mapped_column(Text)
    logprobs: Mapped[list | None] = mapped_column(ARRAY(JSONB(astext_type=Text())))
    completion: Mapped[str | None] = mapped_column(Text)
    original: Mapped[str | None] = mapped_column(Text)
    model_type: Mapped[str | None] = mapped_column(Enum("base", "chat", "image_prompt", name="model_type"))
    finish_reason: Mapped[str | None] = mapped_column(Text)
    harmful: Mapped[bool | None] = mapped_column(Boolean)
    expiration_time: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))
    file_urls: Mapped[list | None] = mapped_column(ARRAY(Text()))

    # completion_: Mapped[Completion | None] = relationship("Completion", back_populates="message")

    children: Mapped[list["Message"] | None] = relationship(back_populates="parent_", foreign_keys=[parent])
    parent_: Mapped[Optional["Message"]] = relationship(
        back_populates="children", remote_side=[id], foreign_keys=[parent]
    )

    # prompt_template: Mapped[PromptTemplate | None] = relationship("PromptTemplate", back_populates="message")
    # label: Mapped[list[Label]] = relationship("Label", back_populates="message_")
