from datetime import UTC, datetime

from fastapi import status
from httpx import AsyncClient

from api.async_message_repository.async_message_repository import AsyncMessageRepository
from api.message.label.label_create_service import LabelCreateRequest, LabelRequest
from core.label.rating import Rating
from core.message.role import Role
from core.object_id import new_id_generator
from db.models.label import Label as LabelModel
from e2e.conftest import AuthenticatedClient, DatabaseSession, auth_headers_for_user
from e2e.create_test_thread import create_test_message


def label_request_url(message_id: str, label_id: str | None = None):
    return f"/v5/message/{message_id}/label/{label_id or ''}"


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

    labels = LabelCreateRequest(
        labels=[
            LabelRequest(
                rating=Rating.POSITIVE,
                comment="N.C.",
            )
        ]
    )

    response = await client.put(
        label_request_url(message.id), json=labels.model_dump(by_alias=True), headers=auth_headers_for_user(anon_user)
    )
    response.raise_for_status()

    message_response = response.json()

    assert isinstance(message_response["labels"], list)
    assert len(message_response["labels"]) == 1

    label_data = message_response["labels"][0]

    # validate response from server
    #
    assert label_data["rating"] == Rating.POSITIVE
    assert label_data["comment"] == "N.C."
    assert label_data["message"] == message.id
    assert label_data["creator"] == anon_user.client

    # keep? this will have the deleted too
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

    # ... end keep?

    # replace existing

    labels = LabelCreateRequest(
        labels=[
            LabelRequest(
                rating=Rating.NEGATIVE,
                comment="N.C.",
            ),
            LabelRequest(
                rating=Rating.FLAG,
                comment="inapprops",
            ),
        ]
    )

    response = await client.put(
        label_request_url(message.id), json=labels.model_dump(by_alias=True), headers=auth_headers_for_user(anon_user)
    )
    response.raise_for_status()

    message_response = response.json()

    assert isinstance(message_response["labels"], list)
    assert len(message_response["labels"]) == 2

    [negative_rating] = [label for label in message_response["labels"] if label["rating"] == Rating.NEGATIVE]
    [flagged_rating] = [label for label in message_response["labels"] if label["rating"] == Rating.FLAG]

    assert negative_rating
    assert flagged_rating
    assert flagged_rating["comment"] == "inapprops"

    # replace causing a deletetion

    labels = LabelCreateRequest(
        labels=[
            LabelRequest(
                rating=Rating.POSITIVE,
                comment="actually.",
            ),
        ]
    )

    response = await client.put(
        label_request_url(message.id), json=labels.model_dump(by_alias=True), headers=auth_headers_for_user(anon_user)
    )
    response.raise_for_status()

    message_response = response.json()

    assert isinstance(message_response["labels"], list)
    assert len(message_response["labels"]) == 1

    response_label = message_response["labels"][0]

    assert response_label["rating"] == Rating.POSITIVE
    assert response_label["comment"] == "actually."

    # validate internal state
    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        updated_message = await message_repository.get_message_by_id(message.id)

    assert updated_message is not None
    assert len(updated_message.labels) == 4

    assert len([label for label in updated_message.labels if label.deleted is None]) == 1
    assert len([label for label in updated_message.labels if label.deleted is not None]) == 3


async def test_can_create_labels_for_someone_elses_message(
    client: AsyncClient, db_session: DatabaseSession, anon_user: AuthenticatedClient, auth_user: AuthenticatedClient
):
    async with db_session() as session:
        # create message and label for anon user
        message = create_test_message(
            content="[Test] message",
            creator=anon_user.client,
            role=Role.Assistant.value,
        )
        message.labels = [
            LabelModel(
                creator=anon_user.client,
                message=message.id,
                rating=Rating.POSITIVE,
                comment="a comment",
            )
        ]
        session.add(message)
        await session.commit()

    # create labels for auth user
    auth_user_labels = LabelCreateRequest(
        labels=[
            LabelRequest(
                rating=Rating.POSITIVE,
                comment="no comment.",
            )
        ]
    )

    response = await client.put(
        label_request_url(message.id),
        json=auth_user_labels.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    response.raise_for_status()

    message_response = response.json()
    assert isinstance(message_response["labels"], list)
    assert len(message_response["labels"]) == 1

    label_data = message_response["labels"][0]

    assert label_data["rating"] == Rating.POSITIVE
    assert label_data["comment"] == "no comment."
    assert label_data["message"] == message.id
    assert label_data["creator"] == auth_user.client

    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        updated_message = await message_repository.get_message_by_id(message.id)

    assert updated_message is not None
    assert len(updated_message.labels) == 2

    # auth user changes their labels (replacing one)
    auth_user_labels = LabelCreateRequest(
        labels=[
            LabelRequest(
                rating=Rating.NEGATIVE,
                comment="changed my mind",
            ),
            LabelRequest(
                rating=Rating.FLAG,
                comment="flagging this",
            ),
        ],
    )

    response = await client.put(
        label_request_url(message.id),
        json=auth_user_labels.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    response.raise_for_status()

    message_response = response.json()
    assert isinstance(message_response["labels"], list)
    assert len(message_response["labels"]) == 2

    [negative_label] = [label for label in message_response["labels"] if label["rating"] == Rating.NEGATIVE]
    [flagged_label] = [label for label in message_response["labels"] if label["rating"] == Rating.FLAG]

    assert negative_label["comment"] == "changed my mind"
    assert flagged_label["comment"] == "flagging this"

    # check internal state
    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        updated_message = await message_repository.get_message_by_id(message.id)

    assert updated_message is not None

    assert len([label for label in updated_message.labels if label.deleted is not None]) == 1
    assert len([label for label in updated_message.labels if label.deleted is None]) == 3


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

    response = await client.delete(label_request_url(message.id, label_id), headers=auth_headers_for_user(anon_user))
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

    response = await client.delete(label_request_url(message.id, label_id), headers=auth_headers_for_user(auth_user))
    assert response.status_code == status.HTTP_403_FORBIDDEN

    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        updated_message = await message_repository.get_message_by_id(message.id)

    assert updated_message is not None
    assert len(updated_message.labels) == 1
    assert updated_message.labels[0].deleted is None
