from httpx import AsyncClient

from e2e.conftest import AuthenticatedClient, auth_headers_for_user

PUBLIC_MODEL_ENDPOINT = "/v5/models/"
ADMIN_MODEL_CONFIG_ENDPOINT = "/v5/admin/models/"


async def list_public_models(
    client: AsyncClient,
    user: AuthenticatedClient,
) -> list[dict]:
    response = await client.get(
        PUBLIC_MODEL_ENDPOINT,
        headers=auth_headers_for_user(user),
    )
    response.raise_for_status()
    return response.json()

public_models_count = 0
internal_models_count = 0


async def test_get_public_models(client: AsyncClient, anon_user: AuthenticatedClient):
    response = await list_public_models(client, anon_user)

    # should have at least one model entity
    public_models_count = len(response)
    assert public_models_count > 0

    # all entities should be public models with specific properties
    for entity in response:
        # should have the following fields that match the model response
        assert "host" in entity
        assert "availableTime" not in entity
        assert "deprecationTime" not in entity

        # all public models should have these values
        assert entity["isVisible"] is True, f"Model {entity.get('id')} has isVisible={entity.get('isVisible')}"
        assert entity["isDeprecated"] is False, (
            f"Model {entity.get('id')} has isDeprecated={entity.get('isDeprecated')}"
        )
        assert entity["internal"] is False, f"Model {entity.get('id')} has internal={entity.get('internal')}"


async def test_get_internal_models(client: AsyncClient, auth_user: AuthenticatedClient):
    response = await list_public_models(client, auth_user)

    # should have at least one model entity
    internal_models_count = len(response)
    assert internal_models_count > 0
    assert internal_models_count > public_models_count, (
        f"There should be more models returned for an authenticated user than an anonymous user. "
        f"Got internal_models_count={internal_models_count}, public_models_count={public_models_count}"
    )

    # all entities should be public models with specific properties
    for entity in response:
        # should have the following fields that match the model response
        assert "host" in entity
        assert "availableTime" not in entity
        assert "deprecationTime" not in entity

        # all public models should have these values
        assert entity["isVisible"] is True, f"Model {entity.get('id')} has isVisible={entity.get('isVisible')}"
        assert entity["isDeprecated"] is False, (
            f"Model {entity.get('id')} has isDeprecated={entity.get('isDeprecated')}"
        )
