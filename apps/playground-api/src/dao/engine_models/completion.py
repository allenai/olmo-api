import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Integer,
    PrimaryKeyConstraint,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from src.dao.engine_models.message import Message


class Completion(Base):
    __tablename__ = "completion"
    __table_args__ = (PrimaryKeyConstraint("id", name="completion_pkey"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    input: Mapped[str] = mapped_column(Text)
    outputs: Mapped[dict] = mapped_column(JSONB)
    opts: Mapped[dict] = mapped_column(JSONB)
    model: Mapped[str] = mapped_column(Text)
    sha: Mapped[str] = mapped_column(Text)
    created: Mapped[datetime.datetime] = mapped_column(DateTime(True), server_default=text("now()"))
    tokenize_ms: Mapped[int] = mapped_column(Integer)
    generation_ms: Mapped[int] = mapped_column(Integer)
    queue_ms: Mapped[int] = mapped_column(Integer)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)

    message: Mapped[list["Message"]] = relationship("Message", back_populates="completion_")
