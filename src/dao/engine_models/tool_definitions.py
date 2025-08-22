import datetime
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSONB, DateTime, Enum, ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src import obj

from .base import Base

if TYPE_CHECKING:
    from src.dao.engine_models.message import Message


class ToolSource(StrEnum):
    # where did this tool come from
    INTERNAL = "internal"
    USER_DEFINED = "user_defined"


@dataclass
class PropertiesType:
    property_type: str
    description: str


@dataclass
class ParameterDef:
    param_type: str
    properties: dict[str, PropertiesType]


class ToolDefinition(Base, kw_only=True):
    __tablename__ = "tool_definition"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default_factory=obj.new_id_generator("td"))

    tool_name: Mapped[str]
    description: Mapped[str]

    param: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)

    tool_source: Mapped[ToolSource] = mapped_column(Enum(ToolSource))

    created: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), nullable=False, server_default=text("now()"), init=False
    )

    message_id: Mapped[str] = mapped_column(ForeignKey("message.id"))
    message: Mapped["Message"] = relationship(back_populates="tool_definitions", init=False)
