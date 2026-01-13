from pathlib import Path

import pytest
from psycopg import AsyncConnection
from pydantic import Field
from pytest_postgresql import factories
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.config import Settings
from api.db.sqlalchemy_engine import get_session
from db.url import make_url
from main import app


# Inherit settings from API -- add additional test related settings
class TestSettings(Settings):
    E2E_AUTH0_CLIENT_ID: str = Field(init=False)
    E2E_AUTH0_CLIENT_SECRET: str = Field(init=False)


settings = TestSettings()

# Set up database for fixtures
postgresql_proc = factories.postgresql_proc(
    load=[
        Path("./schema/01-local.sql"),
        Path("./schema/02-schema.sql"),
        Path("./schema/03-add_models.sql"),
    ],
)

postgresql = factories.postgresql("postgresql_proc")


@pytest.fixture(autouse=True)
async def db_session(postgresql: AsyncConnection):
    db_url = f"postgresql+psycopg://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"
    engine = create_async_engine(make_url(db_url))
    Session = async_sessionmaker(engine, expire_on_commit=False)  # noqa: N806

    async def override_get_session():
        async with Session() as session:
            yield session

    # Override `get_sesion` depenency for tests
    app.dependency_overrides[get_session] = override_get_session

    yield

    await engine.dispose()
    app.dependency_overrides.clear()
