from fastapi import APIRouter

from api.event import event_router
from api.model_config.admin.model_config_admin_router import model_config_admin_router
from api.prompt_template.prompt_template_router import prompt_template_router
from api.user.user_router import user_router

v5_router = APIRouter(prefix="/v5")


# public routes
v5_router.include_router(event_router)
v5_router.include_router(prompt_template_router)
v5_router.include_router(user_router)

# admin routes
v5_router.include_router(model_config_admin_router, prefix="/admin")
