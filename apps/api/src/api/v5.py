from fastapi import APIRouter

from api.auth.auth_service import AuthServiceDependency
from api.event import event_router
from api.model_config.admin.model_config_admin_router import model_config_admin_router

v5_router = APIRouter(prefix="/v5")


v5_router.include_router(event_router)


@v5_router.get("/whoami")
def whoami(auth_service: AuthServiceDependency) -> dict:
    """
    Stub of whoami for e2e testing

    TODO: Update with full whoami including database lookup
    """
    token = auth_service.optional_auth()
    return {
        "client": token.client,
        "is_anonymous": token.is_anonymous_user,
    }


v5_router.include_router(model_config_admin_router, prefix="/admin")
