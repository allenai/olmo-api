from api.attribution.models.document import ResponseAttributionDocument
from api.attribution.models.span import TopLevelAttributionSpan
from core.api_interface import APIInterface


class AttributionResponse(APIInterface):
    index: str
    documents: list[ResponseAttributionDocument]
    spans: list[TopLevelAttributionSpan]
