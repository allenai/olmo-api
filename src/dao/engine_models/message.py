import datetime
from typing import Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.dao.engine_models.completion import Completion
from src.dao.engine_models.label import Label
from src.dao.engine_models.prompt_template import PromptTemplate
from src.dao.message import TokenLogProbs

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

    id: Mapped[str] = mapped_column(primary_key=True)
    content: Mapped[str]
    creator: Mapped[str]
    role: Mapped[str]
    opts: Mapped[dict]
    root: Mapped[str] = mapped_column(ForeignKey("message.id"))
    created: Mapped[datetime.datetime] = mapped_column(server_default=func.now(), init=False)
    final: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), default=False)
    private: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), default=False)
    model_id: Mapped[str]
    model_host: Mapped[str]
    deleted: Mapped[datetime.datetime | None]
    parent: Mapped[str | None] = mapped_column(ForeignKey("message.id"), default=None)
    template: Mapped[str | None] = mapped_column(default=None)
    logprobs: Mapped[list[list[TokenLogProbs]] | None] = mapped_column(ARRAY(JSONB(astext_type=Text())), default=None)
    completion: Mapped[str | None] = mapped_column(default=None, init=False)
    original: Mapped[str | None] = mapped_column(default=None)
    model_type: Mapped[str | None] = mapped_column(Enum("base", "chat", "image_prompt", name="model_type"))
    finish_reason: Mapped[str | None] = mapped_column(default=None)
    harmful: Mapped[bool] = mapped_column(default=False)
    expiration_time: Mapped[datetime.datetime | None] = mapped_column(default=None)
    file_urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text), default=None)

    completion_: Mapped[Completion | None] = relationship("Completion", back_populates="message")

    children: Mapped[list["Message"] | None] = relationship(
        back_populates="parent_", lazy="joined", join_depth=1, foreign_keys=[parent]
    )
    parent_: Mapped[Optional["Message"]] = relationship(
        back_populates="children", remote_side=[id], foreign_keys=[parent]
    )

    prompt_template: Mapped[PromptTemplate | None] = relationship("PromptTemplate", back_populates="message")
    label: Mapped[list[Label]] = relationship("Label", back_populates="message_")
