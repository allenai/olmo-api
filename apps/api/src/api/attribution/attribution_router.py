from fastapi import APIRouter

from api.attribution.attribution_service import AttributionServiceDependency
from api.attribution.models.request import AttributionRequest
from api.attribution.models.response import AttributionResponse
from api.auth.auth_service import AuthServiceDependency

attribution_router = APIRouter(prefix="/attribution")


@attribution_router.post("/")
async def get_attribution(
    request: AttributionRequest,
    auth_service: AuthServiceDependency,
    attribution_service: AttributionServiceDependency,
) -> AttributionResponse:
    auth_service.optional_auth()  # ensure auth
    return await attribution_service.get_attribution(request=request)
