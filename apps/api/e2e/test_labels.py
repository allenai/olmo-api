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

async def test_two_users_creating_deleting_labels(
    client: AsyncClient, db_session: DatabaseSession, auth_user: AuthenticatedClient, anon_user: AuthenticatedClient
):
    async with db_session() as session:
        message = create_test_message(
            content="[Test] message",
            creator=auth_user.client,
            role=Role.Assistant.value,
        )
        session.add(message)
        await session.commit()

    authed_user_label = LabelCreateRequest(
        message=message.id,
        rating=Rating.POSITIVE,
        comment="N.C.",
    )

    # CREATE: AUTHED user label
    authed_user_resp = await client.post(
        LABELS_ENDPOINT, json=authed_user_label.model_dump(by_alias=True), headers=auth_headers_for_user(auth_user)
    )
    authed_user_resp.raise_for_status()
    auth_label_data = authed_user_resp.json()


    anon_user_label = LabelCreateRequest(
        message=message.id,
        rating=Rating.NEGATIVE,
        comment="no comment.",
    )

    # CREATE: ANON user label
    #
    anon_user_resp = await client.post(
        LABELS_ENDPOINT, json=anon_user_label.model_dump(by_alias=True), headers=auth_headers_for_user(anon_user)
    )
    anon_user_resp.raise_for_status()
    anon_label_data = anon_user_resp.json()

    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        message_with_labels = await message_repository.get_message_by_id(message.id)

    assert message_with_labels is not None
    assert len(message_with_labels.labels) == 2

    creators_with_rating = {
        auth_user.client: Rating.POSITIVE,
        anon_user.client: Rating.NEGATIVE,
    }

    for label in message_with_labels.labels:
        assert label.deleted is None
        assert label.rating == creators_with_rating[label.creator]

    # DELETE: ANON user label
    #
    anon_del_response = await client.delete(
        f"{LABELS_ENDPOINT}{anon_label_data['id']}", headers=auth_headers_for_user(anon_user)
    )
    anon_del_response.raise_for_status()

    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        msg_after_one_del = await message_repository.get_message_by_id(message.id)

    assert msg_after_one_del is not None

    # status: one deleted, one not
    # list of deleted labels
    deleted_labels = [lbl for lbl in msg_after_one_del.labels if lbl.deleted]
    assert len(deleted_labels) == 1
    assert deleted_labels[0].creator == anon_user.client
    assert deleted_labels[0].rating == Rating.NEGATIVE
    # list of not deleted labels
    non_deleted_labels = [lbl for lbl in msg_after_one_del.labels if not lbl.deleted]
    assert len(non_deleted_labels) == 1
    assert non_deleted_labels[0].creator == auth_user.client
    assert non_deleted_labels[0].rating == Rating.POSITIVE

    # DELETE: AUTH user label
    #
    auth_del_response = await client.delete(
        f"{LABELS_ENDPOINT}{auth_label_data['id']}", headers=auth_headers_for_user(auth_user)
    )
    auth_del_response.raise_for_status()

    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        msg_after_two_del = await message_repository.get_message_by_id(message.id)

    assert msg_after_two_del is not None

    # list of deleted
    assert msg_after_two_del is not None
    deleted_labels = [lbl for lbl in msg_after_two_del.labels if lbl.deleted]
    assert len(deleted_labels) == 2
    # list of not deleted
    non_deleted_labels = [lbl for lbl in msg_after_two_del.labels if not lbl.deleted]
    assert len(non_deleted_labels) == 0

    # CREATE: new ANON user label
    #
    anon_new_label = LabelCreateRequest(
        message=message.id,
        rating=Rating.FLAG,
        comment="not a comment",
    )
    anon_user_resp_second = await client.post(
        LABELS_ENDPOINT, json=anon_new_label.model_dump(by_alias=True), headers=auth_headers_for_user(anon_user)
    )
    anon_user_resp_second.raise_for_status()

    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        message_with_three_labels = await message_repository.get_message_by_id(message.id)

    assert message_with_three_labels is not None
    assert len(message_with_three_labels.labels) == 3

    # current state: 2 deleted - 1 not deleted
    # list of deleted labels
    deleted_labels_two = [lbl for lbl in message_with_three_labels.labels if lbl.deleted]
    assert len(deleted_labels_two) == 2
    # list of not deleted labels
    non_deleted_labels_one = [lbl for lbl in message_with_three_labels.labels if not lbl.deleted]
    assert len(non_deleted_labels_one) == 1
    assert non_deleted_labels_one[0].rating == Rating.FLAG
    assert non_deleted_labels_one[0].comment == "not a comment"

    # CREATE: new AUTHED user label
    #
    auth_new_label = LabelCreateRequest(
        message=message.id,
        rating=Rating.NEGATIVE,
        comment="authed comment",
    )
    auth_user_resp_second = await client.post(
        LABELS_ENDPOINT, json=auth_new_label.model_dump(by_alias=True), headers=auth_headers_for_user(auth_user)
    )
    auth_user_resp_second.raise_for_status()


    async with db_session() as session:
        message_repository = AsyncMessageRepository(session=session)
        message_with_four_labels = await message_repository.get_message_by_id(message.id)

    # current state -- 2 deleted - 2 not deleted
    assert message_with_four_labels is not None
    assert len(message_with_four_labels.labels) == 4

    non_delted_labels = [lbl for lbl in message_with_four_labels.labels if not lbl.deleted]

    creators_with_comment = {
        auth_user.client: ("authed comment", Rating.NEGATIVE),
        anon_user.client: ("not a comment", Rating.FLAG),
    }

    for label in non_delted_labels:
        (comment, rating) = creators_with_comment[label.creator]
        assert label.comment == comment
        assert label.rating == rating


# async def test_two_users_creating_and_deleting_labels(
#     client: AsyncClient, db_session: DatabaseSession, anon_user: AuthenticatedClient
# ):
#     async with db_session() as session:
#         message = create_test_message(
#             content="[Test] message",
#             creator=anon_user.client,
#             role=Role.Assistant.value,
#         )
#         session.add(message)
#         await session.commit()

#     label = LabelCreateRequest(
#         message=message.id,
#         rating=Rating.POSITIVE,
#         comment="N.C.",
#     )

#     response = await client.post(
#         LABELS_ENDPOINT, json=label.model_dump(by_alias=True), headers=auth_headers_for_user(anon_user)
#     )
#     response.raise_for_status()

#     label_data = response.json()

#     label_id = label_data["id"]

#     response = await client.delete(
#         f"{LABELS_ENDPOINT}{label_id}", headers=auth_headers_for_user(anon_user)
#     )
#     response.raise_for_status()

#     async with db_session() as session:
#         message_repository = AsyncMessageRepository(session=session)
#         message_with_labels = await message_repository.get_message_by_id(message.id)


#     assert message_with_labels is not None
#     assert len(message_with_labels.labels) == 1
#     assert message_with_labels.labels[0].deleted is not None

#     # label_data = response.json()

#     # # validate response from server
#     # #
#     # assert label_data["rating"] == 1
#     # assert label_data["comment"] == "N.C."
#     # assert label_data["message"] == message.id
#     # assert label_data["creator"] == anon_user.client

#     # async with db_session() as session:
#     #     message_repository = AsyncMessageRepository(session=session)
#     #     updated_message = await message_repository.get_message_by_id(message.id)

#     # assert updated_message is not None
#     # assert len(updated_message.labels) == 1
#     # label_from_message = updated_message.labels[0]
#     # assert label_from_message.rating == Rating.POSITIVE
#     # assert label_from_message.creator == anon_user.client
#     # assert label_from_message.comment == "N.C."
#     # assert label_from_message.deleted is None

# async def test_can_replace_label():
