from datetime import datetime

from flask import request
from pydantic import Field
from werkzeug import exceptions

from src import db
from src.api_interface import APIInterface
from src.dao.flask_sqlalchemy_session import current_session
from src.dao.message.message_repository import MessageRepository
from src.dao.user import User
from src.hubspot_service import create_contact
from src.message.GoogleCloudStorage import GoogleCloudStorage


class UpsertUserRequest(APIInterface):
    client: str
    id: str | None = None
    terms_accepted_date: datetime | None = None
    acceptance_revoked_date: datetime | None = None
    data_collection_accepted_date: datetime | None = None
    data_collection_acceptance_revoked_date: datetime | None = None


def upsert_user(dbc: db.Client, client: str, *, should_create_contact: bool) -> User | None:
    request = _map_and_validate_upsert_user_request(client)

    user = dbc.user.get_by_client(request.client)

    if user is not None:
        return dbc.user.update(
            client=request.client,
            id=request.id,
            terms_accepted_date=request.terms_accepted_date,
            acceptance_revoked_date=request.acceptance_revoked_date,
            data_collection_accepted_date=request.data_collection_accepted_date,
            data_collection_acceptance_revoked_date=request.data_collection_acceptance_revoked_date,
        )

    new_user = dbc.user.create(
        client=request.client,
        terms_accepted_date=request.terms_accepted_date,
        acceptance_revoked_date=request.acceptance_revoked_date,
        data_collection_accepted_date=request.data_collection_accepted_date,
        data_collection_acceptance_revoked_date=request.data_collection_acceptance_revoked_date,
    )

    if should_create_contact and new_user:
        create_contact()

    return new_user


def _map_and_validate_upsert_user_request(client: str):
    if request.json is None:
        msg = "no request body"
        raise exceptions.BadRequest(msg)

    return UpsertUserRequest(client=client, **request.json)


class MigrateFromAnonymousUserRequest(APIInterface):
    anonymous_user_id: str = Field()
    new_user_id: str = Field()


class MigrateFromAnonymousUserResponse(APIInterface):
    updated_user: User | None = Field()
    messages_updated_count: int = Field()


def migrate_user_from_anonymous_user(
    dbc: db.Client, storage_client: GoogleCloudStorage, anonymous_user_id: str, new_user_id: str
):
    # migrate tos
    previous_user = dbc.user.get_by_client(anonymous_user_id)
    new_user = dbc.user.get_by_client(new_user_id)

    updated_user = None

    if previous_user is not None and new_user is not None:
        most_recent_terms_accepted_date = max(previous_user.terms_accepted_date, new_user.terms_accepted_date)
        most_recent_data_collection_accepted_date = max(
            (
                d
                for d in [previous_user.data_collection_accepted_date, new_user.data_collection_accepted_date]
                if d is not None
            ),
            default=None,
        )

        # TODO: carry over acceptance revoked date

        updated_user = dbc.user.update(
            client=new_user_id,
            terms_accepted_date=most_recent_terms_accepted_date,
            data_collection_accepted_date=most_recent_data_collection_accepted_date,
        )

    elif previous_user is not None and new_user is None:
        updated_user = dbc.user.create(
            client=new_user_id,
            terms_accepted_date=previous_user.terms_accepted_date,
            acceptance_revoked_date=previous_user.acceptance_revoked_date,
            data_collection_accepted_date=previous_user.data_collection_accepted_date,
            data_collection_acceptance_revoked_date=previous_user.data_collection_acceptance_revoked_date,
        )

    elif previous_user is None and new_user is not None:
        updated_user = new_user

    message_repository = MessageRepository(current_session)

    msgs_to_be_migrated = message_repository.get_by_creator(anonymous_user_id)

    for index, msg in enumerate(msgs_to_be_migrated):
        # 1. migrate anonyous files on Google Cloud
        for url in msg.file_urls or []:
            filename = url.split("/")[-1]
            whole_name = f"{msg.root}/{filename}"
            storage_client.migrate_anonymous_file(whole_name)

    updated_messages_count = message_repository.migrate_messages_to_new_user(
        previous_user_id=anonymous_user_id, new_user_id=new_user_id
    )

    return MigrateFromAnonymousUserResponse(
        updated_user=updated_user,
        messages_updated_count=updated_messages_count,
    )
