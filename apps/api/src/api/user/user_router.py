from fastapi import APIRouter

from api.auth.auth_service import AuthServiceDependency
from api.auth.permission_service import PermissionServiceDependency
from api.user.user_service import LAST_TERMS_UPDATE_DATE, UserServiceDependency
from core.auth.authenticated_client import AuthenticatedClient

user_router = APIRouter(prefix="/user")


@user_router.get("/whoami")
async def get_user(
    auth_service: AuthServiceDependency,
    user_service: UserServiceDependency,
    permission_service: PermissionServiceDependency,
) -> AuthenticatedClient:
    """
    Get information for the current authenticated user.

    Returns user authentication status, terms acceptance, and permissions.
    """
    token = auth_service.optional_auth()

    user = await user_service.get_by_client(token.client)

    # A user is considered to have accepted the latest terms if:
    # - they exist,
    # - their acceptance date is set,
    # - and they accepted on or after the latest terms update,
    #   OR if they revoked before terms update. (see const LAST_TERMS_UPDATE_DATE)
    has_accepted_terms_and_conditions = not (
        user is None
        or user.terms_accepted_date is None
        or (
            user.terms_accepted_date < LAST_TERMS_UPDATE_DATE
            and (user.acceptance_revoked_date is None or user.acceptance_revoked_date < LAST_TERMS_UPDATE_DATE)
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

    has_accepted_media_collection = (
        user is not None
        and user.media_collection_accepted_date is not None
        and (
            user.media_collection_acceptance_revoked_date is None
            or user.media_collection_acceptance_revoked_date < user.media_collection_accepted_date
        )
    )

    # Extract permissions from token using injected PermissionService
    permissions = permission_service.get_permissions(token)

    return AuthenticatedClient(
        id=user.id if user is not None else None,
        client=token.client,
        has_accepted_terms_and_conditions=has_accepted_terms_and_conditions,
        has_accepted_data_collection=has_accepted_data_collection,
        has_accepted_media_collection=has_accepted_media_collection,
        permissions=permissions,
    )
