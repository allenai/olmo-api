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


def upsert_user(dbc: db.Client, client: str) -> Optional[User]:
    request = _map_and_validate_upsert_user_request(client)

    user = dbc.user.get_by_client(request.client)

    if user is not None:
        updated_user = dbc.user.update(
            client=request.client,
            id=request.id,
            terms_accepted_date=request.terms_accepted_date,
            acceptance_revoked_date=request.acceptance_revoked_date,
        )

        return updated_user
    else:
        new_user = dbc.user.create(
            client=request.client,
            terms_accepted_date=request.terms_accepted_date,
            acceptance_revoked_date=request.acceptance_revoked_date,
        )

        return new_user


def _map_and_validate_upsert_user_request(client: str):
    if request.json is None:
        raise exceptions.BadRequest("no request body")

    return UpsertUserRequest(client=client, **request.json)
