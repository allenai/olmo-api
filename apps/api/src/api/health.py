from fastapi import APIRouter, status

from api.db.sqlalchemy import SessionDependency
from sqlalchemy import select

health_router = APIRouter(prefix="/health")


# Standard k8 health check route
@health_router.get("/", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def health(session: SessionDependency) -> None:
    async with session.begin():
        await session.execute(select(1))
