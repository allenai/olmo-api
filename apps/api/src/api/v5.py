from fastapi import APIRouter

from api.auth.auth_service import AuthServiceDependency
from api.config import settings
from api.model_config.admin.model_config_admin_router import model_config_admin_router

v5_router = APIRouter(prefix="/v5")


@v5_router.get("/hello")
def hello_world() -> str:
    return "Hello world"


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


if not settings.ENV.is_production:
    v5_router.include_router(model_config_admin_router, prefix="/admin")
