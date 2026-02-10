from fastapi import APIRouter

from api.attribution.attribution_service import AttributionResponse, AttributionServiceDependency, GetAttributionRequest
from api.model_config.admin.model_config_admin_read_service import ModelConfigAdminReadServiceDependency
from api.service_errors import NotFoundError

attribution_router = APIRouter(prefix="/attribution")


@attribution_router.post("/")
async def get_attribution(
    request: GetAttributionRequest,
    model_config_service: ModelConfigAdminReadServiceDependency,
    attribution_service: AttributionServiceDependency,
) -> AttributionResponse:
    config = await model_config_service.get_one(request.model_id)
    if config is None:
        model_config_not_found = f"Model config {request.model_id} was not found."
        raise NotFoundError(model_config_not_found)

    # ModelConfig is a root model, so we need `.root` to access
    if config.root.infini_gram_index is None:
        msg = f"Model {config.root.id} does not have an infini gram index configured"
        raise ValueError(msg)

    attribution_response = await attribution_service.get_attribution(request=request, index=config.root.infini_gram_index)

    return attribution_response
