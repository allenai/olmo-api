from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

from api.db.sqlalchemy_engine import SessionDependency
from db.models.user import User

# CONST for valid terms acceptance date
# This should be updated whenever the terms and conditions are updated
# so that we can check if the user has accepted the latest version
LAST_TERMS_UPDATE_DATE = datetime(2025, 12, 16, tzinfo=UTC)


class UserService:
    def __init__(self, session: SessionDependency):
        self.session = session

    async def get_by_client(self, client: str) -> User | None:
        """Get a user by their client ID."""
        stmt = select(User).where(User.client == client)
        result = await self.session.scalars(stmt)
        return result.one_or_none()


UserServiceDependency = Annotated[UserService, Depends()]
