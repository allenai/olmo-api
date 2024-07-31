from dataclasses import dataclass
from operator import itemgetter
from typing import List, Optional, cast

from flask import request
from werkzeug import exceptions

from src.api_interface import APIInterface
from src.attribution.infini_gram_api_client.api.default import (
    get_document_attributions_index_attribution_post,
)
from src.attribution.infini_gram_api_client.models.attribution_request import (
    AttributionRequest,
)
from src.attribution.infini_gram_api_client.models.attribution_span_with_documents import (
    AttributionSpanWithDocuments,
)
from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import (
    AvailableInfiniGramIndexId,
)
from src.attribution.infini_gram_api_client.models.http_validation_error import (
    HTTPValidationError,
)
from src.config import cfg

from .infini_gram_api_client import Client


@dataclass
class AttributionDocument:
    text: str
    corresponding_spans: List[str]
    index: str
    source: str
    title: Optional[str]


class GetAttributionRequest(APIInterface):
    model_response: str
    model_id: str
    max_documents: int = 10


class MappedGetAttributionRequest(GetAttributionRequest):
    index: AvailableInfiniGramIndexId


def get_attribution(infini_gram_client: Client) -> dict[int, AttributionDocument]:
    request = _validate_get_attribution_request()
    # TODO: get the correct index for the model
    attribution_response = get_document_attributions_index_attribution_post.sync(
        index=request.index,
        client=infini_gram_client,
        body=AttributionRequest(
            query=request.model_response, include_documents=True, minimum_span_length=10
        ),
    )

    if isinstance(attribution_response, HTTPValidationError):
        # validation error handling
        raise exceptions.InternalServerError(
            description=f"infini-gram API reported a validation error: {attribution_response.detail}\nThis is likely an error in olmo-api."
        )

    if attribution_response is None:
        raise exceptions.BadGateway(
            description="Something went wrong when calling the infini-gram API"
        )

    documents: dict[int, AttributionDocument] = {}
    for span in cast(List[AttributionSpanWithDocuments], attribution_response.spans):
        for document in span.documents:
            if documents.get(document.document_index) is None:
                documents[document.document_index] = AttributionDocument(
                    text=document.text,
                    corresponding_spans=[span.text],
                    index=str(document.document_index),
                    source=document.metadata.additional_properties.get(
                        "metadata", {}
                    ).get("source"),
                    title=document.metadata.additional_properties.get("metadata", {})
                    .get("metadata", {})
                    .get("title", None),
                )
            else:
                documents[document.document_index].corresponding_spans.append(span.text)

    # If we get more documents back than the requestor wants, sort them by their longest corresponding span and return the top X
    if len(documents) > request.max_documents:
        sorted_documents = sorted(
            [
                (id, len(max(document.corresponding_spans, key=len)))
                for (id, document) in documents.items()
            ],
            key=itemgetter(1),
            reverse=True,
        )

        document_tuples_to_return = sorted_documents[slice(request.max_documents)]
        documents_to_return = {
            tuple[0]: documents[tuple[0]] for tuple in document_tuples_to_return
        }

        return documents_to_return

    return documents


def _validate_get_attribution_request():
    if request.json is None:
        raise exceptions.BadRequest("no request body")

    try:
        model_id = request.json.get("model_id")
        index = AvailableInfiniGramIndexId(cfg.infini_gram.model_index_map[model_id])
    except AttributeError:
        raise exceptions.BadRequest(
            description=f"model_id must be one of: [{', '.join(cfg.infini_gram.model_index_map.keys())}]."
        )

    return MappedGetAttributionRequest(**request.json, index=index)
