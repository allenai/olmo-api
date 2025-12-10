from datetime import datetime

from flask import request
from werkzeug import exceptions

from src import db
from src.api_interface import APIInterface
from src.dao.user import User
from src.hubspot_service import create_contact


class UpsertUserRequest(APIInterface):
    client: str
    id: str | None = None
    terms_accepted_date: datetime | None = None
    acceptance_revoked_date: datetime | None = None
    data_collection_accepted_date: datetime | None = None
    data_collection_acceptance_revoked_date: datetime | None = None
    media_collection_accepted_date: datetime | None = None
    media_collection_acceptance_revoked_date: datetime | None = None


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
            media_collection_accepted_date=request.media_collection_accepted_date,
            media_collection_acceptance_revoked_date=request.media_collection_acceptance_revoked_date,
        )

    new_user = dbc.user.create(
        client=request.client,
        terms_accepted_date=request.terms_accepted_date,
        acceptance_revoked_date=request.acceptance_revoked_date,
        data_collection_accepted_date=request.data_collection_accepted_date,
        data_collection_acceptance_revoked_date=request.data_collection_acceptance_revoked_date,
        media_collection_accepted_date=request.media_collection_accepted_date,
        media_collection_acceptance_revoked_date=request.media_collection_acceptance_revoked_date,
    )

    if should_create_contact and new_user:
        create_contact()

    return new_user


def _map_and_validate_upsert_user_request(client: str):
    if request.json is None:
        msg = "no request body"
        raise exceptions.BadRequest(msg)

    return UpsertUserRequest(client=client, **request.json)
