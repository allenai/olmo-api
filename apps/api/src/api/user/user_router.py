from fastapi import APIRouter

from api.auth.auth_service import AuthServiceDependency
from api.user.user_migration_service import UserMigrationRequest, UserMigrationResponse, UserMigrationServiceDependency
from api.user.user_service import UpsertUserRequest, UpsertUserResponse, UserServiceDependency
from api.user.user_who_am_i_service import UserWhoAmIServiceDependency
from core.auth.authenticated_client import AuthenticatedClient

user_router = APIRouter(prefix="/user")


@user_router.get("/whoami")
async def get_who_am_i(
    auth_service: AuthServiceDependency,
    who_am_i_service: UserWhoAmIServiceDependency,
) -> AuthenticatedClient:
    """
    Get information for the current authenticated user.

    Returns user authentication status, terms acceptance, and permissions.
    """
    token = auth_service.optional_auth()

    auth_client = await who_am_i_service.get_by_client(token)

    return auth_client


@user_router.put("/")
async def upsert_user(
    request: UpsertUserRequest,
    auth_service: AuthServiceDependency,
    user_service: UserServiceDependency,
) -> UpsertUserResponse | None:
    """
    Create or update a user record.

    Accepts user info and creates or updates the user in the database.
    For authenticated (non-anonymous) users, also creates a HubSpot contact.
    """
    token = auth_service.optional_auth()

    user = await user_service.upsert_user(request, token)

    return user


@user_router.put("/migration")
async def migrate_user(
    request: UserMigrationRequest,
    auth_service: AuthServiceDependency,
    user_migration_service: UserMigrationServiceDependency,
) -> UserMigrationResponse:
    """
    Migrates annonymous user data to the logged in user account.

    Accepts an anonymous user ID.
    """
    token = auth_service.require_auth()

    user = await user_migration_service.migrate_user_from_anonymous_user(request, token)

    return user
