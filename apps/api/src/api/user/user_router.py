from fastapi import APIRouter

from api.auth.auth_service import AuthServiceDependency
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
