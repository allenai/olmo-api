from typing import Annotated, AsyncGenerator

from api.config import settings
from db.url import make_url
from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession

url = make_url(settings.DATABASE_URL)

engine = create_async_engine(url)

Session = async_sessionmaker(engine)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with Session() as session:
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_session)]

__all__ = ("get_session", "SessionDependency")
