"""E2E tests for user migration from anonymous to authenticated users."""

from httpx import AsyncClient

from e2e.conftest import AuthenticatedClient, add_user_to_database, auth_headers_for_user

USER_MIGRATION_ENDPOINT = "/v5/user/migration"
WHOAMI_ENDPOINT = "/v5/user/whoami"
TEST_ANON_CLIENT = "test_anonymous_user_client"  # from SQL fixture (05-add_test_migration_users.sql)
BOGUS_ANON_CLIENT = "non_existent_anon_client"


async def test_migration_requires_authenticated_user_authentication(
    client: AsyncClient, anon_user: AuthenticatedClient
):
    """Test that migration requires the requesting user to be an authenticated user."""
    response = await client.put(
        USER_MIGRATION_ENDPOINT,
        headers=auth_headers_for_user(anon_user),  # Using anonymous token, not authenticated
        json={
            "anonymousUserId": TEST_ANON_CLIENT,
        },
    )

    assert response.status_code == 401, "Expected 401 Unauthorized migration called by anonymous user"


async def test_migrate_when_both_anonymous_user_and_authenticated_user_exist(
    client: AsyncClient, auth_user: AuthenticatedClient
):
    """Test migration when both anonymous and authenticated users exist."""
    await add_user_to_database(
        auth_client=auth_user,
    )

    response = await client.put(
        USER_MIGRATION_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "anonymousUserId": TEST_ANON_CLIENT,
        },
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    result = response.json()

    # Verify results
    assert result["updatedUser"] is not None
    assert result["updatedUser"]["client"] == auth_user.client, (
        "Authenticated user client ID should match after migration"
    )
    assert result["messagesUpdatedCount"] == 2, "Should migrate 2 messages from anonymous user"


async def test_migrate_when_only_anonymous_user_exists(client: AsyncClient, auth_user: AuthenticatedClient):
    """Test migration when only anonymous user exists (authenticated user created in db during migration)."""
    response = await client.put(
        USER_MIGRATION_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "anonymousUserId": TEST_ANON_CLIENT,
        },
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    result = response.json()

    # Verify results
    assert result["updatedUser"] is not None
    assert result["updatedUser"]["client"] == auth_user.client, (
        "Authenticated user client ID should match after migration"
    )
    assert result["messagesUpdatedCount"] == 2, "Should migrate 2 messages from anonymous user"


async def test_migrate_when_only_authenticated_user_exists(client: AsyncClient, auth_user: AuthenticatedClient):
    """Test migration when only authenticated user exists (no anonymous user data)."""
    await add_user_to_database(
        auth_client=auth_user,
    )

    response = await client.put(
        USER_MIGRATION_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "anonymousUserId": BOGUS_ANON_CLIENT,  # Non-existent anonymous user ID
        },
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    result = response.json()

    # Verify results - should return existing auth user with no messages migrated
    assert result["updatedUser"] is None
    assert result["messagesUpdatedCount"] == 0, "No messages to migrate from non-existent anonymous user"


async def test_migrate_when_neither_user_exists(client: AsyncClient, auth_user: AuthenticatedClient):
    """Test migration when neither user exists in the database."""
    response = await client.put(
        USER_MIGRATION_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "anonymousUserId": BOGUS_ANON_CLIENT,  # Non-existent anonymous user ID
        },
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    result = response.json()

    # Verify results - no user created, no messages migrated
    assert result["updatedUser"] is None
    assert result["messagesUpdatedCount"] == 0, "No messages to migrate from non-existent anonymous user"


async def test_migration_idempotency(client: AsyncClient, auth_user: AuthenticatedClient):
    """Test that running migration twice doesn't cause errors."""
    await add_user_to_database(
        auth_client=auth_user,
    )

    response1 = await client.put(
        USER_MIGRATION_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "anonymousUserId": TEST_ANON_CLIENT,
        },
    )
    assert response1.status_code == 200
    result1 = response1.json()

    # Second migration (should be safe to run again)
    response2 = await client.put(
        USER_MIGRATION_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "anonymousUserId": TEST_ANON_CLIENT,
        },
    )
    assert response2.status_code == 200
    result2 = response2.json()

    # Both should succeed
    assert result1["messagesUpdatedCount"] == 2  # 2 messages migrated first time
    assert result2["messagesUpdatedCount"] == 0  # No messages after second migration
