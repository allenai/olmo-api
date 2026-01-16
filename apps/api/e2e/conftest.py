import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient, Client
from psycopg import AsyncConnection
from pydantic import Field
from pytest_postgresql import factories
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.config import Settings
from api.db.sqlalchemy_engine import get_session
from db.url import make_url
from main import app

ANONYMOUS_USER_ID_HEADER = "X-Anonymous-User-ID"


@dataclass(kw_only=True)
class AuthenticatedClient:
    client: str
    token: str | None
    is_anonymous: bool = False


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
        Path("./schema/04-add_prompt_templates.sql"),
    ],
)

postgresql = factories.postgresql("postgresql_proc")


# Generic (auth/anon) make user helper function
async def make_user(*, client: AsyncClient, auth0_token: str | None = None, anonymous=False) -> AuthenticatedClient:
    if anonymous:
        user_id = str(uuid.uuid4())
        headers = {ANONYMOUS_USER_ID_HEADER: user_id}
    else:
        headers = {"Authorization": f"Bearer {auth0_token}"}

    response = await client.get("/v5/whoami", headers=headers)
    response.raise_for_status()
    client_id = response.json().get("client")
    return AuthenticatedClient(client=client_id, token=auth0_token, is_anonymous=anonymous)


# get the correct headers for user type
def auth_headers_for_user(user: AuthenticatedClient) -> dict[str, str]:
    if user.is_anonymous:
        return {ANONYMOUS_USER_ID_HEADER: str(user.client)}
    return {"Authorization": f"Bearer {user.token}"}


@pytest.fixture(autouse=True)
async def db_session(postgresql: AsyncConnection):
    db_url = f"postgresql+psycopg://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"
    engine = create_async_engine(make_url(db_url))

    async with engine.connect() as connection:
        transaction = await connection.begin()

        Session = async_sessionmaker(bind=connection, expire_on_commit=False)  # noqa: N806

        async def override_get_session():
            async with Session() as session:
                yield session

        # Override `get_session` dependency for tests
        app.dependency_overrides[get_session] = override_get_session

        yield

        await transaction.rollback()
        app.dependency_overrides.clear()

    await engine.dispose()


@pytest.fixture
async def client():
    """Async client fixture"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="session")
def auth0_token() -> str:
    payload = {
        "client_id": settings.E2E_AUTH0_CLIENT_ID,
        "client_secret": settings.E2E_AUTH0_CLIENT_SECRET,
        "audience": settings.AUTH_AUDIENCE,
        "grant_type": "client_credentials",
    }
    headers = {"content-type": "application/json"}

    with Client() as client:
        response = client.post(
            f"https://{settings.AUTH_DOMAIN}/oauth/token", json=payload, headers=headers, timeout=5.0
        )
        response.raise_for_status()

        return response.json().get("access_token")


@pytest.fixture
async def auth_user(client: AsyncClient, auth0_token: str) -> AuthenticatedClient:
    return await make_user(client=client, auth0_token=auth0_token)


@pytest.fixture
async def anon_user(client: AsyncClient) -> AuthenticatedClient:
    return await make_user(client=client, anonymous=True)
