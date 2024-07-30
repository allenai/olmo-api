from dataclasses import dataclass
from typing import List, Optional

from flask import request
from werkzeug import exceptions

from src.api_interface import APIInterface
from src.attribution.infini_gram_api_client.api.default import (
    get_document_attributions_index_attribution_post,
)
from src.attribution.infini_gram_api_client.models.attribution_request import (
    AttributionRequest,
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
    max_documents: Optional[int] = 10


def get_attribution(infini_gram_client: Client) -> dict[int, AttributionDocument]:
    request = _validate_get_attribution_request()
    index = cfg.infini_gram.model_index_map[request.model_id]
    # TODO: get the correct index for the model
    attribution_response = get_document_attributions_index_attribution_post.sync(
        index=index,
        client=infini_gram_client,
        body=AttributionRequest(
            query=request.model_response, include_documents=True, minimum_span_length=10
        ),
    )

    if isinstance(attribution_response, HTTPValidationError):
        # validation error handling
        raise exceptions.InternalServerError()

    if attribution_response is None:
        raise exceptions.BadGateway()

    # if isinstance(attribution_response, InfiniGramAttributionResponseWithDocs):
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
                    title=document.metadata.additional_properties.get("metadata", {})
                    .get("metadata", {})
                    .get("title", None),
                )
            else:
                documents[document.document_index].corresponding_spans.append(span.text)
    return documents


def _validate_get_attribution_request():
    if request.json is None:
        raise exceptions.BadRequest("no request body")

    return GetAttributionRequest(**request.json)
