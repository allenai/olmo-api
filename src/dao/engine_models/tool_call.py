from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src import obj
from src.dao.engine_models.tool_definitions import ToolSource

from .base import Base

if TYPE_CHECKING:
    from src.dao.engine_models.message import Message


class ToolCall(Base, kw_only=True):
    __tablename__ = "tool_call"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default_factory=obj.new_id_generator("tc"))
    tool_call_id: Mapped[str] = mapped_column(Text)
    tool_name: Mapped[str]

    tool_source: Mapped[ToolSource] = mapped_column(Enum(ToolSource), nullable=False)
    args: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)

    message_id: Mapped[str] = mapped_column(ForeignKey("message.id"))
    message: Mapped["Message"] = relationship("Message", back_populates="tool_calls", init=False)
