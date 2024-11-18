from datetime import datetime
from typing import Optional

from flask import request
from pydantic import Field
from werkzeug import exceptions

from src import db
from src.api_interface import APIInterface
from src.dao.user import User
from src.hubspot_service import create_contact


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

        if new_user:
            create_contact()

        return new_user


def _map_and_validate_upsert_user_request(client: str):
    if request.json is None:
        raise exceptions.BadRequest("no request body")

    return UpsertUserRequest(client=client, **request.json)


class MigrateFromAnonymousUserRequest(APIInterface):
    anonymous_user_id: str = Field()
    new_user_id: str = Field()


class MigrateFromAnonymousUserResponse(APIInterface):
    updated_user: Optional[User] = Field()
    messages_updated_count: int = Field()


def migrate_user_from_anonymous_user(
    dbc: db.Client, anonymous_user_id: str, new_user_id: str
):
    # migrate tos
    previous_user = dbc.user.get_by_client(anonymous_user_id)
    new_user = dbc.user.get_by_client(new_user_id)

    updated_user = None

    if previous_user is not None and new_user is not None:
        most_recent_terms_accepted_date = max(
            previous_user.terms_accepted_date, new_user.terms_accepted_date
        )

        # TODO: carry over acceptance revoked date

        updated_user = dbc.user.update(
            client=new_user_id, terms_accepted_date=most_recent_terms_accepted_date
        )

    elif previous_user is not None and new_user is None:
        updated_user = dbc.user.create(
            client=new_user_id,
            terms_accepted_date=previous_user.terms_accepted_date,
            acceptance_revoked_date=previous_user.acceptance_revoked_date,
        )

    elif previous_user is None and new_user is not None:
        updated_user = new_user

    updated_messages_count = dbc.message.migrate_messages_to_new_user(
        previous_user_id=anonymous_user_id, new_user_id=new_user_id
    )

    return MigrateFromAnonymousUserResponse(
        updated_user=updated_user,
        messages_updated_count=updated_messages_count,
    )
