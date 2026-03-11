import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from unittest.mock import create_autospec

import pytest
from httpx import ASGITransport, AsyncClient, Client
from main import app
from psycopg import AsyncConnection
from pydantic import Field
from pytest_postgresql import factories
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from typing_extensions import override

from api.config import Settings
from api.db.sqlalchemy_engine import get_session
from api.gcs_dependency import get_google_cloud_storage
from api.test_utils.fake_mcp_server import test_toolset
from api.thread.chat.safety.image_safety_checker_service import get_imaage_safety_checker
from api.thread.chat.safety.safety_checkers.safety_checker_base import (
    SafetyCheckUnsafeError,
    SafetyChecker,
    SafetyCheckRequest,
    SafetyCheckResponse,
)
from api.thread.chat.safety.text_safety_checker_service import get_text_safety_checker
from api.tools.mcp_service import McpService
from core.google_cloud_storage import GoogleCloudStorage, UploadResponse
from core.tools.tool_source import ToolSource
from db.models.tool_definitions import ToolDefinition
from db.models.user import User
from db.url import make_url

ANONYMOUS_USER_ID_HEADER = "X-Anonymous-User-ID"


DatabaseSession = async_sessionmaker[AsyncSession]


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
        Path("./schema/05-add_test_migration_users.sql"),
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

    response = await client.get("/v5/user/whoami", headers=headers)
    response.raise_for_status()
    client_id = response.json().get("client")
    return AuthenticatedClient(client=client_id, token=auth0_token, is_anonymous=anonymous)


# get the correct headers for user type
def auth_headers_for_user(user: AuthenticatedClient) -> dict[str, str]:
    if user.is_anonymous:
        return {ANONYMOUS_USER_ID_HEADER: str(user.client)}
    return {"Authorization": f"Bearer {user.token}"}


async def add_user_to_database(db_session: DatabaseSession, auth_client: AuthenticatedClient) -> User:
    """Add a user directly to the database.

    Args:
        auth_client: The authenticated client object

    Returns:
        The created or existing User object
    """
    # Check if user already exists
    async with db_session() as session, session.begin():
        stmt = select(User).where(User.client == auth_client.client)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return existing_user

        new_user = User(
            client=auth_client.client,
            terms_accepted_date=datetime.now(UTC),
            acceptance_revoked_date=None,
            data_collection_accepted_date=None,
            data_collection_acceptance_revoked_date=None,
            media_collection_accepted_date=None,
            media_collection_acceptance_revoked_date=None,
        )
        session.add(new_user)
        await session.flush()
    return new_user


@pytest.fixture(autouse=True)
async def db_session(postgresql: AsyncConnection):
    db_url = f"postgresql+psycopg://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"
    engine = create_async_engine(make_url(db_url))

    Session = async_sessionmaker(engine, expire_on_commit=False)  # noqa: N806

    async def override_get_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    yield Session

    app.dependency_overrides.pop(get_session, None)
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


@pytest.fixture(autouse=True)
def mock_mcp_service():
    """Override McpService to avoid calling real MCP servers"""

    mock_tool = ToolDefinition(
        name="mock_tool",
        tool_source=ToolSource.MCP,
        mcp_server_id="mock-server",
        description="A mock tool for testing",
        parameters={"type": "object", "properties": {}},
    )

    class _MockMcpService:
        @classmethod
        async def get_general_mcp_tools(cls):
            return [mock_tool]

        @classmethod
        async def get_tools_from_mcp_servers(cls, _mcp_server_ids: set[str]):
            return [mock_tool]

        @classmethod
        def get_pydantic_ai_mcp_servers(cls):
            return [test_toolset]

    app.dependency_overrides[McpService] = _MockMcpService

    yield

    app.dependency_overrides.pop(McpService, None)


@pytest.fixture(autouse=True)
def mock_google_cloud_storage():

    def mock_google_cloud_storage():
        mock = create_autospec(
            GoogleCloudStorage,
            spec_set=True,
        )

        def upload_content_side_effect(
            filename: str,
            file_data: BinaryIO | bytes,  # noqa: ARG001
            *,
            bucket_name: str,
            content_type: str | None = None,  # noqa: ARG001
            make_file_public: bool = False,  # noqa: ARG001
        ) -> UploadResponse:
            return UploadResponse(
                public_url=f"http://localhost:8888/{filename}", storage_path=f"foo://{bucket_name}/{filename}"
            )

        mock.upload_content.side_effect = upload_content_side_effect

        return mock

    app.dependency_overrides[get_google_cloud_storage] = mock_google_cloud_storage

    yield

    app.dependency_overrides.pop(get_google_cloud_storage, None)


def _make_safety_checker_mock(*, is_safe: bool) -> type[SafetyChecker]:
    class _Response(SafetyCheckResponse):
        @override
        def is_safe(self) -> bool:
            return is_safe

    class _MockChecker(SafetyChecker):
        @override
        async def check_request(self, request: SafetyCheckRequest, *, throw: bool = False) -> SafetyCheckResponse:
            response = _Response()
            if not response.is_safe() and throw:
                raise SafetyCheckUnsafeError
            return response

    return _MockChecker


@pytest.fixture(autouse=True)
def mock_text_safety_checker():
    app.dependency_overrides[get_text_safety_checker] = _make_safety_checker_mock(is_safe=True)
    yield
    app.dependency_overrides.pop(get_text_safety_checker, None)


@pytest.fixture(autouse=True)
def mock_image_safety_checker():
    app.dependency_overrides[get_imaage_safety_checker] = _make_safety_checker_mock(is_safe=True)
    yield
    app.dependency_overrides.pop(get_imaage_safety_checker, None)


@pytest.fixture
def mock_unsafe_text_safety_checker():
    app.dependency_overrides[get_text_safety_checker] = _make_safety_checker_mock(is_safe=False)
    yield
    app.dependency_overrides.pop(get_text_safety_checker, None)


@pytest.fixture
def mock_unsafe_image_safety_checker():
    app.dependency_overrides[get_imaage_safety_checker] = _make_safety_checker_mock(is_safe=False)
    yield
    app.dependency_overrides.pop(get_imaage_safety_checker, None)
