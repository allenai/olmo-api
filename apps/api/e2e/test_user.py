from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from httpx import AsyncClient

from e2e.conftest import AuthenticatedClient, auth_headers_for_user

USER_ENDPOINT = "/v5/user/"
WHOAMI_ENDPOINT = "/v5/user/whoami"


def iso_datetimes_equal(actual_iso: str, expected_datetime: datetime) -> bool:
    """Helper to compare ISO datetime strings with datetime objects, accounting for timezone differences."""
    actual_dt = datetime.fromisoformat(actual_iso)
    expected_utc = expected_datetime.astimezone(UTC)
    actual_utc = actual_dt.astimezone(UTC)

    return actual_utc == expected_utc


async def test_upsert_user_fails_without_auth(client: AsyncClient):
    response = await client.put(
        USER_ENDPOINT,
        json={
            "termsAcceptedDate": datetime.now(ZoneInfo("America/New_York")).isoformat(),
        },
    )
    assert response.status_code == 401, "Expected 401 when accessing user endpoint without auth"


async def test_anonymous_user_can_create_anonymous_user_record(client: AsyncClient, anon_user: AuthenticatedClient):
    terms_accepted_date = datetime.now(ZoneInfo("America/New_York"))

    response = await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(anon_user),
        json={
            "termsAcceptedDate": terms_accepted_date.isoformat(),
        },
    )
    assert response.status_code == 200, (
        f"Anonymous users should be able to create anonymous user records, got {response.status_code}"
    )

    payload = response.json()
    assert payload["client"] == anon_user.client, "Client ID should match anonymous user"


async def test_terms_acceptance_fields(client: AsyncClient, auth_user: AuthenticatedClient):
    terms_accepted_date = datetime.now(ZoneInfo("America/New_York"))
    acceptance_revoked_date = terms_accepted_date + timedelta(days=1)

    # Create user with terms acceptance
    response = await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "termsAcceptedDate": terms_accepted_date.isoformat(),
        },
    )
    assert response.status_code == 200, f"Expected 200 when creating user, got {response.status_code}"

    payload = response.json()
    assert payload["client"] == auth_user.client, "Client ID should match authenticated user"
    assert iso_datetimes_equal(payload["termsAcceptedDate"], terms_accepted_date), (
        "Terms accepted date should be same as provided date"
    )

    # Revoke acceptance
    revoke_response = await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "acceptanceRevokedDate": acceptance_revoked_date.isoformat(),
        },
    )

    payload = revoke_response.json()
    assert payload["client"] == auth_user.client, "Client ID should match authenticated user"
    assert iso_datetimes_equal(payload["termsAcceptedDate"], terms_accepted_date), (
        "Terms accepted date should be same as provided revoked date"
    )
    assert iso_datetimes_equal(payload["acceptanceRevokedDate"], acceptance_revoked_date), (
        "Acceptance revoked date should be same as provided revokeddate"
    )


async def test_terms_acceptance_status_in_whoami(client: AsyncClient, auth_user: AuthenticatedClient):
    terms_accepted_date = datetime.now(ZoneInfo("America/New_York"))
    acceptance_revoked_date = terms_accepted_date + timedelta(days=1)
    terms_reaccepted_date = acceptance_revoked_date + timedelta(days=1)

    # Create user with terms acceptance
    await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "termsAcceptedDate": terms_accepted_date.isoformat(),
        },
    )

    # Check whoami endpoint
    response = await client.get(WHOAMI_ENDPOINT, headers=auth_headers_for_user(auth_user))
    assert response.status_code == 200, f"Expected 200 from whoami, got {response.status_code}"

    payload = response.json()
    assert payload["hasAcceptedTermsAndConditions"] is True, "User should have accepted T&Cs"

    # Revoke acceptance
    revoke_response = await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "acceptanceRevokedDate": acceptance_revoked_date.isoformat(),
        },
    )

    assert revoke_response.status_code == 200, (
        f"Expected 200 when revoking acceptance, got {revoke_response.status_code}"
    )

    # Re-accept with new date
    re_accept_response = await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "termsAcceptedDate": terms_reaccepted_date.isoformat(),
        },
    )

    assert re_accept_response.status_code == 200, (
        f"Expected 200 when re-accepting terms, got {re_accept_response.status_code}"
    )

    # Check whoami endpoint shows user has accepted again
    response = await client.get(WHOAMI_ENDPOINT, headers=auth_headers_for_user(auth_user))
    assert response.status_code == 200, f"Expected 200 from whoami, got {response.status_code}"

    payload = response.json()
    assert payload["hasAcceptedTermsAndConditions"] is True, (
        "User should have accepted T&Cs after re-accepting following revocation"
    )


async def test_data_collection_consent_fields(client: AsyncClient, auth_user: AuthenticatedClient):
    data_collection_accepted_date = datetime.now(ZoneInfo("America/New_York"))

    # Create user with data collection acceptance
    response = await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "termsAcceptedDate": data_collection_accepted_date.isoformat(),
            "dataCollectionAcceptedDate": data_collection_accepted_date.isoformat(),
        },
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    payload = response.json()
    assert payload["client"] == auth_user.client, "Client ID should match authenticated user"
    assert iso_datetimes_equal(payload["dataCollectionAcceptedDate"], data_collection_accepted_date), (
        "Data collection accepted date should be same as provided date"
    )


async def test_data_collection_consent_status_in_whoami(client: AsyncClient, auth_user: AuthenticatedClient):
    data_collection_accepted_date = datetime.now(ZoneInfo("America/New_York"))
    data_collection_revoked_date = data_collection_accepted_date + timedelta(days=1)

    # Create user with data collection acceptance
    await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "termsAcceptedDate": data_collection_accepted_date.isoformat(),
            "dataCollectionAcceptedDate": data_collection_accepted_date.isoformat(),
        },
    )

    # Check whoami endpoint
    response = await client.get(WHOAMI_ENDPOINT, headers=auth_headers_for_user(auth_user))
    assert response.status_code == 200, f"Expected 200 from whoami, got {response.status_code}"

    payload = response.json()
    assert payload["hasAcceptedDataCollection"] is True, "User should have accepted data collection"

    # update user with data collection revocation
    await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "termsAcceptedDate": data_collection_revoked_date.isoformat(),
            "dataCollectionAcceptanceRevokedDate": data_collection_revoked_date.isoformat(),
        },
    )

    # Check whoami endpoint
    response = await client.get(WHOAMI_ENDPOINT, headers=auth_headers_for_user(auth_user))
    assert response.status_code == 200, f"Expected 200 from whoami, got {response.status_code}"

    payload = response.json()
    assert payload["hasAcceptedDataCollection"] is False, "User should have revoked data collection"


async def test_media_collection_consent_fields(client: AsyncClient, auth_user: AuthenticatedClient):
    media_collection_accepted_date = datetime.now(ZoneInfo("America/New_York"))

    # Create user with media collection acceptance
    response = await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "termsAcceptedDate": media_collection_accepted_date.isoformat(),
            "mediaCollectionAcceptedDate": media_collection_accepted_date.isoformat(),
        },
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    payload = response.json()
    assert payload["client"] == auth_user.client, "Client ID should match authenticated user"
    assert iso_datetimes_equal(payload["mediaCollectionAcceptedDate"], media_collection_accepted_date), (
        "Media collection accepted date should be same as provided date"
    )


async def test_media_collection_consent_status_in_whoami(client: AsyncClient, auth_user: AuthenticatedClient):
    media_collection_accepted_date = datetime.now(ZoneInfo("America/New_York"))
    media_collection_revoked_date = media_collection_accepted_date + timedelta(days=1)

    # Create user with media collection acceptance
    await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "termsAcceptedDate": media_collection_accepted_date.isoformat(),
            "mediaCollectionAcceptedDate": media_collection_accepted_date.isoformat(),
        },
    )

    # Check whoami endpoint
    response = await client.get(WHOAMI_ENDPOINT, headers=auth_headers_for_user(auth_user))
    assert response.status_code == 200, f"Expected 200 from whoami, got {response.status_code}"

    payload = response.json()
    assert payload["hasAcceptedMediaCollection"] is True, "User should have accepted media collection"

    # Update user with media collection revocation
    await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "termsAcceptedDate": media_collection_revoked_date.isoformat(),
            "mediaCollectionAcceptanceRevokedDate": media_collection_revoked_date.isoformat(),
        },
    )

    # Check whoami endpoint
    response = await client.get(WHOAMI_ENDPOINT, headers=auth_headers_for_user(auth_user))
    assert response.status_code == 200, f"Expected 200 from whoami, got {response.status_code}"

    payload = response.json()
    assert payload["hasAcceptedMediaCollection"] is False, "User should have revoked media collection"
