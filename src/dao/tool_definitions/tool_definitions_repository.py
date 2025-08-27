import abc
from collections.abc import Sequence
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session


from src.dao.engine_models.tool_definitions import ToolDefinition, ToolSource


class BaseToolDefinitionsRepository(abc.ABC):
    @abc.abstractmethod
    def get_active_internal_tool_definitions(
        self,
    ) -> Sequence[ToolDefinition]:
        raise NotImplementedError


class ToolDefinitionsRepository(BaseToolDefinitionsRepository):
    session: Session

    def get_active_internal_tool_definitions(
        self,
    ) -> Sequence[ToolDefinition]:
        stmt = select(ToolDefinition).where(
            ToolDefinition.tool_source == ToolSource.INTERNAL,
            ToolDefinition.active == True,
        )
        return self.session.scalars(stmt).unique().all()
