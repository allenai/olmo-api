from httpx import AsyncClient

from .conftest import AuthenticatedClient, auth_headers_for_user

THREADS_ENDPOINT = "/v5/threads/"


async def test_threads_lists_for_anon_user(client: AsyncClient, anon_user: AuthenticatedClient):
    response = await client.get(THREADS_ENDPOINT, headers=auth_headers_for_user(anon_user))

    assert response.status_code == 200, f"{response.url} responded with an non-success for an anonymous user"

    response_obj = response.json()

    # shape
    assert isinstance(response_obj["meta"], dict)
    assert isinstance(response_obj["threads"], list)
    # values
    assert response_obj["meta"]["total"] == 0
    assert len(response_obj["threads"]) == 0


async def test_threads_list_for_authed_user():
    pass
