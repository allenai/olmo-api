from dataclasses import dataclass
from typing import List, Optional

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

from .infini_gram_api_client import Client


@dataclass
class AttributionDocument:
    text: str
    corresponding_spans: List[str]
    index: str
    source: str
    title: Optional[str]


def get_attribution(
    model_response: str,
    model_id: str,
    infini_gram_client: Client,
    max_documents: int = 10,
):
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
        documents: dict[int, AttributionDocument] = {}
        for span in attribution_response.spans:
            for document in span.documents:
                if documents.get(document.document_index) is None:
                    documents[document.document_index] = AttributionDocument(
                        text=document.text,
                        corresponding_spans=[span.text],
                        index=str(document.document_index),
                        source=document.metadata.additional_properties.get(
                            "metadata", {}
                        ).get("source"),
                        title=document.metadata.additional_properties.get(
                            "metadata", {}
                        )
                        .get("metadata", {})
                        .get("title", None),
                    )
                else:
                    documents[document.document_index].corresponding_spans.append(
                        span.text
                    )
        return documents
