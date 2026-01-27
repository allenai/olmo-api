from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient

from e2e.conftest import AuthenticatedClient, auth_headers_for_user

USER_ENDPOINT = "/v5/user/"
WHOAMI_ENDPOINT = "/v5/user/whoami"


async def test_upsert_user_fails_without_auth(client: AsyncClient):
    response = await client.put(
        USER_ENDPOINT,
        json={
            "termsAcceptedDate": datetime.now(ZoneInfo("America/New_York")).isoformat(),
        },
    )
    assert response.status_code == 401, "Expected 401 when accessing user endpoint without auth"


async def test_anonymous_user_cannot_create_user_record(client: AsyncClient, anon_user: AuthenticatedClient):
    # Anonymous users get 401 because require_auth() is used
    terms_accepted_date = datetime.now(ZoneInfo("America/New_York"))

    response = await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(anon_user),
        json={
            "termsAcceptedDate": terms_accepted_date.isoformat(),
        },
    )
    # The endpoint uses require_auth() which rejects anonymous users
    assert response.status_code == 401, "Anonymous users should get 401 from user endpoint"


@pytest.mark.skip(reason="Timezone assertion issue in test infrastructure")
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
    assert payload["termsAcceptedDate"] == terms_accepted_date.astimezone(UTC).isoformat(), (
        "Terms accepted date should be in UTC"
    )

    # Revoke acceptance
    await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "acceptanceRevokedDate": acceptance_revoked_date.isoformat(),
        },
    )

    payload = response.json()
    assert payload["client"] == auth_user.client, "Client ID should match authenticated user"
    assert payload["termsAcceptedDate"] == terms_accepted_date.astimezone(UTC).isoformat(), (
        "Terms accepted date should be in UTC"
    )
    assert payload["acceptanceRevokedDate"] == acceptance_revoked_date.astimezone(UTC).isoformat(), (
        "Acceptance revoked date should be in UTC"
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
    await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "acceptanceRevokedDate": acceptance_revoked_date.isoformat(),
        },
    )

    # Re-accept with new date
    await client.put(
        USER_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
        json={
            "termsAcceptedDate": terms_reaccepted_date.isoformat(),
        },
    )

    # Check whoami endpoint shows user has accepted again
    response = await client.get(WHOAMI_ENDPOINT, headers=auth_headers_for_user(auth_user))
    assert response.status_code == 200, f"Expected 200 from whoami, got {response.status_code}"

    payload = response.json()
    assert payload["hasAcceptedTermsAndConditions"] is True, (
        "User should have accepted T&Cs after re-accepting following revocation"
    )


@pytest.mark.skip(reason="Timezone assertion issue in test infrastructure")
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
    assert payload["dataCollectionAcceptedDate"] == data_collection_accepted_date.astimezone(UTC).isoformat(), (
        "Data collection accepted date should be in UTC"
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


@pytest.mark.skip(reason="Timezone assertion issue in test infrastructure")
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
    assert payload["mediaCollectionAcceptedDate"] == media_collection_accepted_date.astimezone(UTC).isoformat(), (
        "Media collection accepted date should be in UTC"
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
