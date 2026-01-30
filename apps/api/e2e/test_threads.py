from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select, update

from core.message.role import Role
from db.models.message import Message
from db.models.model_config import ModelConfig
from e2e.conftest import AuthenticatedClient, auth_headers_for_user
from e2e.create_test_thread import create_test_message, create_test_thread

THREADS_ENDPOINT = "/v5/threads/"


async def test_threads_lists_empty_for_auth_user(client: AsyncClient, auth_user: AuthenticatedClient):
    response = await client.get(THREADS_ENDPOINT, headers=auth_headers_for_user(auth_user))

    assert response.status_code == 200, f"{response.url} responded with an non-success for an anonymous user"

    response_obj = response.json()

    # shape
    assert isinstance(response_obj["meta"], dict)
    assert isinstance(response_obj["threads"], list)
    # values
    assert response_obj["meta"]["total"] == 0
    assert len(response_obj["threads"]) == 0


@pytest.mark.skip("this works, but we don't show it in UI")
async def test_threads_lists_empty_for_anon_user(client: AsyncClient, auth_user: AuthenticatedClient):
    response = await client.get(THREADS_ENDPOINT, headers=auth_headers_for_user(auth_user))

    assert response.status_code == 200, f"{response.url} responded with an non-success for an anonymous user"

    response_obj = response.json()

    # shape
    assert isinstance(response_obj["meta"], dict)
    assert isinstance(response_obj["threads"], list)
    # values
    assert response_obj["meta"]["total"] == 0
    assert len(response_obj["threads"]) == 0


async def test_threads_list_for_authed_user(client: AsyncClient, db_session, auth_user: AuthenticatedClient):
    thread_id = await create_test_thread(db_session=db_session, user=auth_user)

    response = await client.get(THREADS_ENDPOINT, headers=auth_headers_for_user(auth_user))
    response.raise_for_status()
    thread_data = response.json()

    assert thread_data["meta"]["total"] == 1
    assert len(thread_data["threads"]) == 1
    assert thread_data["threads"][0]["id"] == thread_id

    # has messages
    assert len(thread_data["threads"][0]["messages"]) == 3


@pytest.mark.skip("this works, but we don't show it in UI")
async def test_threads_lists_for_anon_user(client: AsyncClient, db_session, anon_user: AuthenticatedClient):
    thread_id = await create_test_thread(db_session=db_session, user=anon_user)

    response = await client.get(THREADS_ENDPOINT, headers=auth_headers_for_user(anon_user))
    response.raise_for_status()
    thread_data = response.json()

    assert thread_data["meta"]["total"] == 1
    assert len(thread_data["threads"]) == 1
    assert thread_data["threads"][0]["id"] == thread_id

    # has messages
    assert len(thread_data["threads"][0]["messages"]) == 3


async def test_threads_lists_for_authed_user(client: AsyncClient, db_session, auth_user: AuthenticatedClient):
    thread_id = await create_test_thread(db_session=db_session, user=auth_user)

    response = await client.get(THREADS_ENDPOINT, headers=auth_headers_for_user(auth_user))
    response.raise_for_status()
    thread_data = response.json()

    assert thread_data["meta"]["total"] == 1
    assert len(thread_data["threads"]) == 1
    assert thread_data["threads"][0]["id"] == thread_id

    # has messages
    assert len(thread_data["threads"][0]["messages"]) == 3


async def test_doesnt_show_threads_for_other_user(
    client: AsyncClient, db_session, anon_user: AuthenticatedClient, auth_user: AuthenticatedClient
):
    await create_test_thread(db_session=db_session, user=anon_user)

    response = await client.get(THREADS_ENDPOINT, headers=auth_headers_for_user(auth_user))

    response.raise_for_status()
    response_obj = response.json()

    # auth user response should be empty
    assert isinstance(response_obj["meta"], dict)
    assert isinstance(response_obj["threads"], list)
    assert response_obj["meta"]["total"] == 0
    assert len(response_obj["threads"]) == 0


async def test_pagination_for_threads_list(client: AsyncClient, db_session, auth_user: AuthenticatedClient):
    for _ in range(5):
        await create_test_thread(db_session=db_session, user=auth_user)

    response = await client.get("/v5/threads/?limit=3", headers=auth_headers_for_user(auth_user))

    assert response.status_code == 200
    data = response.json()

    assert data["meta"]["total"] == 5
    assert len(data["threads"]) == 3

    response = await client.get("/v5/threads/?limit=3&offset=3", headers=auth_headers_for_user(auth_user))

    assert response.status_code == 200
    data = response.json()

    assert data["meta"]["total"] == 5
    assert data["meta"]["offset"] == 3
    assert len(data["threads"]) == 2


async def test_get_nonexistant_thread(client: AsyncClient, anon_user: AuthenticatedClient):
    response = await client.get(f"{THREADS_ENDPOINT}msg_DOESNOTEXIST", headers=auth_headers_for_user(anon_user))

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_valid_thread(client: AsyncClient, db_session, anon_user: AuthenticatedClient):
    thread_id = await create_test_thread(db_session=db_session, user=anon_user)

    response = await client.get(f"{THREADS_ENDPOINT}{thread_id}", headers=auth_headers_for_user(anon_user))
    response.raise_for_status()

    thread_data = response.json()
    assert thread_data["id"] == thread_id

    assert len(thread_data["messages"]) == 3

    # response shape
    assert all("id" in msg for msg in thread_data["messages"])
    assert all("content" in msg for msg in thread_data["messages"])
    assert all("role" in msg for msg in thread_data["messages"])


async def test_auth_user_delete_own_thread(client: AsyncClient, db_session, auth_user: AuthenticatedClient):
    thread_id = await create_test_thread(db_session=db_session, user=auth_user)

    # verify it exists
    response = await client.get(f"{THREADS_ENDPOINT}{thread_id}", headers=auth_headers_for_user(auth_user))
    response.raise_for_status()

    # delete the thread
    delete_response = await client.delete(f"/v5/threads/{thread_id}", headers=auth_headers_for_user(auth_user))
    delete_response.raise_for_status()

    # verify it was deleted
    get_response = await client.get(f"/v5/threads/{thread_id}", headers=auth_headers_for_user(auth_user))
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


async def test_anon_user_cant_delete_their_thread(client: AsyncClient, db_session, anon_user: AuthenticatedClient):
    thread_id = await create_test_thread(db_session=db_session, user=anon_user)
    response = await client.get(f"{THREADS_ENDPOINT}{thread_id}", headers=auth_headers_for_user(anon_user))
    response.raise_for_status()

    # try to delete the thread
    delete_response = await client.delete(f"/v5/threads/{thread_id}", headers=auth_headers_for_user(anon_user))
    assert delete_response.status_code == status.HTTP_403_FORBIDDEN

    # verify it still exists
    response = await client.get(f"{THREADS_ENDPOINT}{thread_id}", headers=auth_headers_for_user(anon_user))
    response.raise_for_status()


async def test_cant_delete_another_users_thread(
    client: AsyncClient, db_session, auth_user: AuthenticatedClient, anon_user: AuthenticatedClient
):
    thread_id = await create_test_thread(db_session=db_session, user=anon_user)
    response = await client.get(f"{THREADS_ENDPOINT}{thread_id}", headers=auth_headers_for_user(anon_user))
    response.raise_for_status()

    # try to delete the thread
    delete_response = await client.delete(f"/v5/threads/{thread_id}", headers=auth_headers_for_user(auth_user))
    assert delete_response.status_code == status.HTTP_403_FORBIDDEN

    # verify it still exists
    response = await client.get(f"{THREADS_ENDPOINT}{thread_id}", headers=auth_headers_for_user(anon_user))
    response.raise_for_status()


async def test_cannot_delete_old_thread(client: AsyncClient, db_session, auth_user: AuthenticatedClient):
    async with db_session() as session, session.begin():
        model_result = await session.scalars(select(ModelConfig).limit(1))
        model = model_result.first()
        if model is None:
            pytest.fail("No models available to test with")

        message = create_test_message(
            content="[Test] old message message",
            creator=auth_user.client,
            role=Role.User.value,
            opts={},
            parent=None,
            model_id=model.id,
            model_host=model.host.value,
            final=True,
            expiration_time=None,
        )
        session.add(message)
        await session.flush()

        # have to update instead of passing to __init__
        await session.execute(
            update(Message).where(Message.id == message.id).values(created=datetime.now(UTC) - timedelta(days=31))
        )

    # Try to delete
    response = await client.delete(f"{THREADS_ENDPOINT}{message.id}", headers=auth_headers_for_user(auth_user))

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_nonexistent_thread(client: AsyncClient, auth_user: AuthenticatedClient):
    response = await client.delete("/v5/threads/msg_DOESNOTEXIST", headers=auth_headers_for_user(auth_user))

    assert response.status_code == status.HTTP_404_NOT_FOUND
