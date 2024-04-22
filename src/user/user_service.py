from datetime import datetime
from typing import Optional

from flask import request
from werkzeug import exceptions

from src import db
from src.api_interface import APIInterface
from src.dao.user import User


class UpsertUserRequest(APIInterface):
    client: str
    id: Optional[str] = None
    terms_accepted_date: Optional[datetime] = None
    acceptance_revoked_date: Optional[datetime] = None


def upsert_user(
    dbc: db.Client, client: str, upsert_user_request: Optional[UpsertUserRequest] = None
) -> Optional[User]:
    mapped_request = (
        _map_and_validate_upsert_user_request(client)
        if upsert_user_request is None
        else upsert_user_request
    )

    user = dbc.user.get_by_client(mapped_request.client)

    if user is not None:
        updated_user = dbc.user.update(
            client=mapped_request.client,
            id=mapped_request.id,
            terms_accepted_date=mapped_request.terms_accepted_date,
            acceptance_revoked_date=mapped_request.acceptance_revoked_date,
        )

        return updated_user
    else:
        new_user = dbc.user.create(
            client=mapped_request.client,
            terms_accepted_date=mapped_request.terms_accepted_date,
            acceptance_revoked_date=mapped_request.acceptance_revoked_date,
        )

        return new_user


def _map_and_validate_upsert_user_request(client: str):
    if request.json is None:
        raise exceptions.BadRequest("no request body")

    return UpsertUserRequest(client=client, **request.json)


class AcceptTermsAndConditionsRequest(UpsertUserRequest):
    acceptance_revoked_date: None


def accept_terms_and_conditions(dbc: db.Client, client: str):
    if request.json is None:
        raise exceptions.BadRequest("no request body")

    mapped_request = AcceptTermsAndConditionsRequest(client=client, **request.json)
    upsert_user(dbc, client, mapped_request)
