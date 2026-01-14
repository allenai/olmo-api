from httpx import AsyncClient

from e2e.conftest import AuthenticatedClient, auth_headers_for_user, make_user

WHOAMI_ENDPOINT = "/v5/whoami"


async def test_whoami_fails_without_auth(client: AsyncClient):
    r = await client.get(WHOAMI_ENDPOINT)
    assert r.status_code == 401, "Expected 401 when accessing whoami without auth"


async def test_whoami_with_anonymous_user(client: AsyncClient, anon_user: AuthenticatedClient):
    r = await client.get(WHOAMI_ENDPOINT, headers=auth_headers_for_user(anon_user))
    assert r.status_code == 200, f"Expected 200 for anonymous user, got {r.status_code}"

    data = r.json()
    assert "client" in data, "Response should contain client field"
    assert data["client"] == anon_user.client, "Client ID should match"
    assert data.get("is_anonymous") is True, "Should be marked as anonymous"


async def test_whoami_with_authenticated_user(client: AsyncClient, auth_user: AuthenticatedClient):
    r = await client.get(WHOAMI_ENDPOINT, headers=auth_headers_for_user(auth_user))
    assert r.status_code == 200, f"Expected 200 for authenticated user, got {r.status_code}"

    data = r.json()
    assert "client" in data, "Response should contain client field"
    assert data["client"] == auth_user.client, "Client ID should match"
    assert data.get("is_anonymous") is False, "Should not be marked as anonymous"


async def test_multiple_anonymous_users_are_distinct(client: AsyncClient):
    user1 = await make_user(client=client, anonymous=True)
    user2 = await make_user(client=client, anonymous=True)

    assert user1.client != user2.client, "Different anonymous users should have different client IDs"


async def test_invalid_bearer_token_returns_401(client: AsyncClient):
    r = await client.get(WHOAMI_ENDPOINT, headers={"Authorization": "Bearer invalid_token_12345"})
    assert r.status_code == 401, "Expected 401 for invalid bearer token"


async def test_malformed_authorization_header_returns_401(client: AsyncClient):
    test_cases = [
        "NotBearer token123",  # Wrong auth scheme
        "Bearer",  # No auth token
        "token123",  # No scheme
    ]

    for auth_header in test_cases:
        r = await client.get(WHOAMI_ENDPOINT, headers={"Authorization": auth_header})
        assert r.status_code == 401, f"Expected 401 for malformed header: {auth_header}"
