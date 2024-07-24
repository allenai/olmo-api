from infini_gram_api_client import Client

from src.attribution.infini_gram_api_client.api.default import (
    get_document_attributions_index_attribution_post,
)
from src.attribution.infini_gram_api_client.models.attribution_request import (
    AttributionRequest,
)
from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import (
    AvailableInfiniGramIndexId,
)
from src.attribution.infini_gram_api_client.models.http_validation_error import (
    HTTPValidationError,
)
from src.attribution.infini_gram_api_client.models.infini_gram_attribution_response_with_docs import (
    InfiniGramAttributionResponseWithDocs,
)
from src.config import cfg


def get_attribution(model_response: str, model_id: str):
    infini_gram_client = Client(base_url=cfg.infini_gram_api_url)
    # TODO: get the correct index for the model
    attribution_response = get_document_attributions_index_attribution_post.sync(
        index=AvailableInfiniGramIndexId.DOLMA_1_7,
        client=infini_gram_client,
        body=AttributionRequest(
            query=model_response, include_documents=True, minimum_span_length=10
        ),
    )

    if isinstance(attribution_response, HTTPValidationError):
        # validation error handling
        ...

    if isinstance(attribution_response, InfiniGramAttributionResponseWithDocs):
        documents = []
        for span in attribution_response.spans:
            for document in span.documents:
                documents.append(document)
