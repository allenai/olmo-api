from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession

from api.config import settings
from db.url import make_url


@lru_cache
def get_sqlalchemy_engine():
    url = make_url(settings.DATABASE_URL)

    engine = create_async_engine(
        url,
        pool_size=settings.DATABASE_MIN_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW_CONNECTIONS,
    )

    return engine


@lru_cache
def get_sessionmaker():
    engine = get_sqlalchemy_engine()

    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    Session = get_sessionmaker()  # noqa: N806
    async with Session() as session:
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_session)]

__all__ = ("SessionDependency", "get_session")
