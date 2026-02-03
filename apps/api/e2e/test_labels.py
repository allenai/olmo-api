from datetime import UTC, datetime

from fastapi import status
from httpx import AsyncClient

from api.async_message_repository.async_message_repository import AsyncMessageRepository
from api.label.label_create_service import LabelCreateRequest
from core.label.rating import Rating
from core.message.role import Role
from core.object_id import new_id_generator
from db.models.label import Label as LabelModel
from e2e.conftest import AuthenticatedClient, DatabaseSession, auth_headers_for_user
from e2e.create_test_thread import create_test_message

LABELS_ENDPOINT = "/v5/labels/"

label_id_generator = new_id_generator("lbl")


async def test_can_create_labels_for_message(
    client: AsyncClient, db_session: DatabaseSession, anon_user: AuthenticatedClient
):
    async with db_session() as session:
        message = create_test_message(
            content="[Test] message",
            creator=anon_user.client,
            role=Role.Assistant.value,
        )
        session.add(message)
        await session.commit()

    label = LabelCreateRequest(
        message=message.id,
        rating=Rating.POSITIVE,
        comment="N.C.",
    )

    response = await client.post(
        LABELS_ENDPOINT, json=label.model_dump(by_alias=True), headers=auth_headers_for_user(anon_user)
    )
    response.raise_for_status()

    label_data = response.json()

    # validate response from server
    #
    assert label_data["rating"] == 1
    assert label_data["comment"] == "N.C."
    assert label_data["message"] == message.id
    assert label_data["creator"] == anon_user.client

    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        updated_message = await message_repository.get_message_by_id(message.id)

    assert updated_message is not None
    assert len(updated_message.labels) == 1
    label_from_message = updated_message.labels[0]
    assert label_from_message.rating == Rating.POSITIVE
    assert label_from_message.creator == anon_user.client
    assert label_from_message.comment == "N.C."
    assert label_from_message.deleted is None


async def test_can_create_labels_for_someone_elses_message(
    client: AsyncClient, db_session: DatabaseSession, anon_user: AuthenticatedClient, auth_user: AuthenticatedClient
):
    async with db_session() as session:
        message = create_test_message(
            content="[Test] message",
            creator=anon_user.client,
            role=Role.Assistant.value,
        )
        session.add(message)
        await session.commit()

    label = LabelCreateRequest(
        message=message.id,
        rating=Rating.NEGATIVE,
        comment="no comment.",
    )

    response = await client.post(
        LABELS_ENDPOINT, json=label.model_dump(by_alias=True), headers=auth_headers_for_user(auth_user)
    )
    response.raise_for_status()

    label_data = response.json()
    assert label_data["rating"] == 0
    assert label_data["comment"] == "no comment."
    assert label_data["message"] == message.id
    assert label_data["creator"] == auth_user.client

    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        updated_message = await message_repository.get_message_by_id(message.id)

    assert updated_message is not None
    assert len(updated_message.labels) == 1
    label_from_message = updated_message.labels[0]
    assert label_from_message.rating == Rating.NEGATIVE
    assert label_from_message.creator == auth_user.client
    assert label_from_message.comment == "no comment."
    assert label_from_message.deleted is None


async def test_can_delete_own_label(client: AsyncClient, db_session: DatabaseSession, anon_user: AuthenticatedClient):
    label_id = label_id_generator()
    async with db_session() as session:
        message = create_test_message(
            content="[Test] message",
            creator=anon_user.client,
            role=Role.Assistant.value,
        )
        message.labels = [
            LabelModel(
                id=label_id,
                creator=anon_user.client,
                message=message.id,
                rating=Rating.POSITIVE,
                comment="a comment",
            )
        ]
        session.add(message)
        await session.commit()

    response = await client.delete(f"{LABELS_ENDPOINT}{label_id}", headers=auth_headers_for_user(anon_user))
    response.raise_for_status()

    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        updated_message = await message_repository.get_message_by_id(message.id)

    assert updated_message is not None
    assert len(updated_message.labels) == 1
    label_from_message = updated_message.labels[0]
    assert label_from_message.deleted is not None
    assert label_from_message.deleted < datetime.now(tz=UTC)


async def test_cannot_delete_someone_elses_label(
    client: AsyncClient, db_session: DatabaseSession, auth_user: AuthenticatedClient, anon_user: AuthenticatedClient
):
    label_id = label_id_generator()
    async with db_session() as session:
        message = create_test_message(
            content="[Test] message",
            creator=anon_user.client,
            role=Role.Assistant.value,
        )
        message.labels = [
            LabelModel(
                id=label_id,
                creator=anon_user.client,
                message=message.id,
                rating=Rating.POSITIVE,
                comment="a comment",
            )
        ]
        session.add(message)
        await session.commit()

    response = await client.delete(f"{LABELS_ENDPOINT}{label_id}", headers=auth_headers_for_user(auth_user))
    assert response.status_code == status.HTTP_403_FORBIDDEN

    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        updated_message = await message_repository.get_message_by_id(message.id)

    assert updated_message is not None
    assert len(updated_message.labels) == 1
    label_from_message = updated_message.labels[0]
    assert label_from_message.deleted is None


async def test_cannot_create_a_new_label_without_deleting(
    client: AsyncClient, db_session: DatabaseSession, auth_user: AuthenticatedClient
):
    label_id = label_id_generator()
    async with db_session() as session:
        message = create_test_message(
            content="[Test] message",
            creator=auth_user.client,
            role=Role.Assistant.value,
        )
        message.labels = [
            LabelModel(
                id=label_id,
                creator=auth_user.client,
                message=message.id,
                rating=Rating.POSITIVE,
                comment="a comment",
            )
        ]
        session.add(message)
        await session.commit()

    label = LabelCreateRequest(
        message=message.id,
        rating=Rating.POSITIVE,
        comment="N.C.",
    )

    response = await client.post(
        LABELS_ENDPOINT, json=label.model_dump(by_alias=True), headers=auth_headers_for_user(auth_user)
    )
    assert response.status_code == status.HTTP_409_CONFLICT
