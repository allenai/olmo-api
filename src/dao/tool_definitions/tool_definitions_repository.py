import abc

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.dao.engine_models.tool_definitions import ToolDefinition, ToolSource


class BaseToolDefinitionsRepository(abc.ABC):
    @abc.abstractmethod
    def get_active_internal_tool_definitions(
        self,
    ) -> list[ToolDefinition]:
        raise NotImplementedError


class ToolDefinitionsRepository(BaseToolDefinitionsRepository):
    session: Session

    def __init__(self, session: Session):
        self.session = session

    def get_active_internal_tool_definitions(
        self,
    ) -> list[ToolDefinition]:
        stmt = select(ToolDefinition).where(
            ToolDefinition.tool_source == ToolSource.INTERNAL,
            ToolDefinition.active == True,
        )
        return list(self.session.scalars(stmt).all())
