from fastapi import APIRouter

from api.attribution.attribution_service import AttributionServiceDependency
from api.attribution.models.request import GetAttributionRequest
from api.attribution.models.response import GetAttributionResponse

attribution_router = APIRouter(prefix="/attribution")


@attribution_router.post("/")
async def get_attribution(
    request: GetAttributionRequest,
    attribution_service: AttributionServiceDependency,
) -> GetAttributionResponse:
    return await attribution_service.get_attribution(request=request)
