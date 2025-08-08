import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    PrimaryKeyConstraint,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from src.dao.engine_models.message import Message


class PromptTemplate(Base):
    __tablename__ = "prompt_template"
    __table_args__ = (PrimaryKeyConstraint("id", name="prompt_template_pkey"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(Text)
    created: Mapped[datetime.datetime] = mapped_column(DateTime(True), server_default=text("now()"))
    updated: Mapped[datetime.datetime] = mapped_column(DateTime(True), server_default=text("now()"))
    deleted: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    message: Mapped[list["Message"]] = relationship("Message", back_populates="prompt_template")
