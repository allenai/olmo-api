"""
User Service (FastAPI) - V4
----------------------------

User service for FastAPI that accepts validated request objects directly
instead of reading from Flask's request context.
"""

from src import db
from src.dao.user import User
from src.hubspot_service import create_contact
from src.user.user_service import UpsertUserRequest


def upsert_user_v4(dbc: db.Client, user_request: UpsertUserRequest, *, should_create_contact: bool, auth_header: str | None = None) -> User | None:
    """
    Create or update a user with validated request object.

    This is the FastAPI version that accepts the validated UpsertUserRequest directly
    instead of reading from Flask's request.json.
    """
    user = dbc.user.get_by_client(user_request.client)

    if user is not None:
        return dbc.user.update(
            client=user_request.client,
            id=user_request.id,
            terms_accepted_date=user_request.terms_accepted_date,
            acceptance_revoked_date=user_request.acceptance_revoked_date,
            data_collection_accepted_date=user_request.data_collection_accepted_date,
            data_collection_acceptance_revoked_date=user_request.data_collection_acceptance_revoked_date,
        )

    new_user = dbc.user.create(
        client=user_request.client,
        terms_accepted_date=user_request.terms_accepted_date,
        acceptance_revoked_date=user_request.acceptance_revoked_date,
        data_collection_accepted_date=user_request.data_collection_accepted_date,
        data_collection_acceptance_revoked_date=user_request.data_collection_acceptance_revoked_date,
    )

    if should_create_contact and new_user and auth_header:
        create_contact(auth_header)

    return new_user
