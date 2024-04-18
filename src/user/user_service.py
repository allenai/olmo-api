from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from flask import request
from werkzeug import exceptions

from src import db
from src.dao.user import User


@dataclass
class UpsertUserRequest:
    client: str
    id: Optional[str] = None
    terms_accepted_date: Optional[datetime] = None
    acceptance_revoked_date: Optional[datetime] = None


def upsert_user(dbc: db.Client, client: str) -> Optional[User]:
    request = _map_and_validate_upsert_user_request(client)

    user = dbc.user.get_by_client(request.client)

    if user is not None:
        return dbc.user.update(
            client=request.client,
            id=request.id,
            terms_accepted_date=request.terms_accepted_date,
            acceptance_revoked_date=request.acceptance_revoked_date,
        )
    else:
        return dbc.user.create(
            client=request.client,
            terms_accepted_date=request.terms_accepted_date,
            acceptance_revoked_date=request.acceptance_revoked_date,
        )


def _map_and_validate_upsert_user_request(client: str):
    if request.json is None:
        raise exceptions.BadRequest("no request body")

    if client is None:
        raise exceptions.BadRequest("client is required")

    terms_accepted_date = request.json.get("termsAcceptedDate")
    mapped_terms_accepted_date = (
        datetime.fromisoformat(terms_accepted_date)
        if terms_accepted_date is not None
        else None
    )

    acceptance_revoked_date = request.json.get("acceptanceRevokedDate")
    mapped_acceptance_revoked_date = (
        datetime.fromisoformat(acceptance_revoked_date)
        if acceptance_revoked_date is not None
        else None
    )

    return UpsertUserRequest(
        client=client,
        id=request.json.get("id"),
        terms_accepted_date=mapped_terms_accepted_date,
        acceptance_revoked_date=mapped_acceptance_revoked_date,
    )
