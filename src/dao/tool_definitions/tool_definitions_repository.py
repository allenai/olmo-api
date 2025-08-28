import abc

from sqlalchemy.orm import Session


class BaseToolDefinitionsRepository(abc.ABC):
    pass


class ToolDefinitionsRepository(BaseToolDefinitionsRepository):
    session: Session

    def __init__(self, session: Session):
        self.session = session
