from fastapi import APIRouter

from api.config import settings
from api.model_config.admin.model_config_admin_router import model_config_admin_router

v5_router = APIRouter(prefix="/v5")


@v5_router.get("/hello")
def hello_world() -> str:
    return "Hello world"


if not settings.ENV.is_production:
    v5_router.include_router(model_config_admin_router, prefix="/admin")
