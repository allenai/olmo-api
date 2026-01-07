from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import Depends

from api.config import settings
from db.url import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession

url = make_url(settings.DATABASE_URL)

engine = create_async_engine(
    url,
    pool_size=settings.DATABASE_MIN_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW_CONNECTIONS,
)

Session = async_sessionmaker(engine)


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    async with Session() as session:
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_session)]

__all__ = ("SessionDependency", "get_session")
