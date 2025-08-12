from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from src.dao.engine_models.message import Message


class ToolCall(Base, kw_only=True):
    __tablename__ = "tool_call"

    tool_call_id: Mapped[str] = mapped_column(primary_key=True)
    tool_name: Mapped[str]
    args: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)

    message_id: Mapped[str] = mapped_column(ForeignKey("message.id"))
    message: Mapped["Message"] = relationship(back_populates="tool_calls", init=False)
