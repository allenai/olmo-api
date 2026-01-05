import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from db.models.message import Message

from .base import Base


class Label(Base):
    __tablename__ = "label"
    __table_args__ = (
        ForeignKeyConstraint(
            ["message"], ["message.id"], ondelete="CASCADE", name="label_message_fkey"
        ),
        PrimaryKeyConstraint("id", name="label_pkey"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    message: Mapped[str] = mapped_column(Text, index=True)
    rating: Mapped[int] = mapped_column(Integer)
    creator: Mapped[str] = mapped_column(Text)
    created: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), server_default=text("now()")
    )
    comment: Mapped[Optional[str]] = mapped_column(Text)
    deleted: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    message_: Mapped["Message"] = relationship("Message", back_populates="labels")
