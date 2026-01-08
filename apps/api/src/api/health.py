from fastapi import APIRouter, status
from sqlalchemy import select

from api.db.sqlalchemy_engine import SessionDependency

health_router = APIRouter()


# Standard k8 health check route
# Using get with path instead of a route prefix to prevent unnecessary redirects
@health_router.get("/health", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def health(session: SessionDependency) -> None:
    async with session.begin():
        await session.execute(select(1))
