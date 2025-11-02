"""
User Router (FastAPI) - V4
---------------------------

FastAPI router for user operations including authentication, user management,
and anonymous user migration.
Converted from Flask blueprint in user_blueprint.py.
"""

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Body, Request

from src.auth.auth_utils import get_permissions
from src.auth.authenticated_client import AuthenticatedClient
from src.auth.fastapi_dependencies import RequiredAuth
from src.dao.user import User
from src.dependencies import DBClient, StorageClient
from src.user.user_migrate import (
    MigrateFromAnonymousUserRequest,
    MigrateFromAnonymousUserResponse,
    UserMigrationServiceDep,
    migrate_user_from_anonymous_user,
)
from src.user.user_service import UpsertUserRequest
from src.user.v4_user_service import upsert_user_v4

router = APIRouter(tags=["v4", "user"])


@router.get("/whoami", response_model=AuthenticatedClient)
async def whoami(
    token: RequiredAuth,
    dbc: DBClient,
) -> AuthenticatedClient:
    """Get info for the current user"""
    user = await asyncio.to_thread(dbc.user.get_by_client, token.client)
    last_terms_update_date = datetime(2025, 7, 11, tzinfo=UTC)

    # A user is considered to have accepted the latest terms if:
    # - they exist,
    # - their acceptance date is set,
    # - and they accepted on or after the latest terms update,
    #   OR if they revoked before terms update.
    has_accepted_terms_and_conditions = not (
        user is None
        or user.terms_accepted_date is None
        or (
            user.terms_accepted_date < last_terms_update_date
            and (user.acceptance_revoked_date is None or user.acceptance_revoked_date < last_terms_update_date)
        )
    )

    has_accepted_data_collection = (
        user is not None
        and user.data_collection_accepted_date is not None
        and (
            user.data_collection_acceptance_revoked_date is None
            or user.data_collection_acceptance_revoked_date < user.data_collection_accepted_date
        )
    )

    return AuthenticatedClient(
        id=user.id if user is not None else None,
        client=token.client,
        has_accepted_terms_and_conditions=has_accepted_terms_and_conditions,
        has_accepted_data_collection=has_accepted_data_collection,
        permissions=get_permissions(token.token),
    )


@router.put("/user", response_model=User | None)
async def update_user(
    request: Request,
    token: RequiredAuth,
    dbc: DBClient,
    user_request: UpsertUserRequest = Body(...),
) -> User | None:
    """Create or update user"""
    should_create_contact = not token.is_anonymous_user

    # Override client from token (security measure)
    user_request.client = token.client

    # Get auth header for hubspot
    auth_header = request.headers.get("Authorization", "")

    return await asyncio.to_thread(
        upsert_user_v4, dbc, user_request=user_request, should_create_contact=should_create_contact, auth_header=auth_header
    )


@router.put("/migrate-user", response_model=MigrateFromAnonymousUserResponse)
async def migrate_from_anonymous_user(
    token: RequiredAuth,
    service: UserMigrationServiceDep,
    dbc: DBClient,
    storage_client: StorageClient,
    migration_request: MigrateFromAnonymousUserRequest = Body(...),
) -> MigrateFromAnonymousUserResponse:
    """Migrate data from anonymous user to authenticated user"""
    # Override new_user_id from token (security measure)
    migration_request.new_user_id = token.token.sub if hasattr(token.token, "sub") else token.client

    return await asyncio.to_thread(
        service.migrate_user_from_anonymous_user,
        dbc=dbc,
        storage_client=storage_client,
        anonymous_user_id=migration_request.anonymous_user_id,
        new_user_id=migration_request.new_user_id,
    )
