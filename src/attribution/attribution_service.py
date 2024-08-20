from dataclasses import dataclass, field
from itertools import islice
from operator import itemgetter
from typing import Iterable, List, Optional, cast

from flask import json, request
from werkzeug import exceptions

from src.api_interface import APIInterface
from src.attribution.infini_gram_api_client.api.default import (
    get_document_attributions_index_attribution_post,
)
from src.attribution.infini_gram_api_client.models.attribution_document import (
    AttributionDocument,
)
from src.attribution.infini_gram_api_client.models.attribution_request import (
    AttributionRequest,
)
from src.attribution.infini_gram_api_client.models.attribution_span import (
    AttributionSpan,
)
from src.attribution.infini_gram_api_client.models.attribution_span_with_documents import (
    AttributionSpanWithDocuments,
)
from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import (
    AvailableInfiniGramIndexId,
)
from src.attribution.infini_gram_api_client.models.document_with_pointer import (
    DocumentWithPointer,
)
from src.attribution.infini_gram_api_client.models.http_validation_error import (
    HTTPValidationError,
)
from src.config import cfg

from .infini_gram_api_client import Client


@dataclass
class ResponseAttributionDocument:
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
    # include_spans_in_root is passed in as the query param includeSpansInRoot=true|false
    include_spans_in_root: bool


@dataclass
class ResponseAttributionSpan:
    text: str
    documents: List[int] = field(default_factory=lambda: [])


@dataclass
class TopLevelSpan:
    text: str
    left: int
    right: int
    nested_spans: Iterable[AttributionSpan | AttributionSpanWithDocuments]
    documents: List[AttributionDocument | DocumentWithPointer]


def collapse_spans(
    spans: Iterable[AttributionSpan | AttributionSpanWithDocuments],
    input_tokens: Iterable[str],
):
    spans_sorted_by_length = sorted(spans, key=lambda span: span.length)

    top_level_spans: List[TopLevelSpan] = []

    for i, span in enumerate(spans_sorted_by_length):
        left = span.left
        right = span.right
        overlapping_spans: List[AttributionSpan | AttributionSpanWithDocuments] = []

        for span_to_check in islice(spans_sorted_by_length, i + 1, -1):
            if (
                left <= span_to_check.left < right
                or left <= span_to_check.right < right
            ):
                overlapping_spans.append(span_to_check)
                left = min(span_to_check.left, left)
                right = max(span_to_check.right, right)

        new_documents = [
            document
            for overlapping_span in overlapping_spans
            for document in overlapping_span.documents
        ]

        text = "".join(islice(input_tokens, left, right))

        if len(overlapping_spans) > 0:
            top_level_spans.append(
                TopLevelSpan(
                    text,
                    left=left,
                    right=right,
                    documents=new_documents,
                    nested_spans=overlapping_spans,
                )
            )


def get_attribution(
    infini_gram_client: Client,
):
    request = _validate_get_attribution_request()
    attribution_response = get_document_attributions_index_attribution_post.sync(
        index=request.index,
        client=infini_gram_client,
        body=AttributionRequest(
            query=request.model_response,
            include_documents=True,
            minimum_span_length=10,
            delimiters=["\n", "."],
            maximum_frequency=10,
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

    # collapsed_spans = collapse_spans(attribution_response.spans)

    documents: dict[int, ResponseAttributionDocument] = {}
    spans: dict[str, ResponseAttributionSpan] = {}
    for span in cast(List[AttributionSpanWithDocuments], attribution_response.spans):
        if spans.get(span.text) is None:
            spans[span.text] = ResponseAttributionSpan(text=span.text)

        for document in span.documents:
            if document.document_index not in spans[span.text].documents:
                spans[span.text].documents.append(document.document_index)

            if documents.get(document.document_index) is None:
                documents[document.document_index] = ResponseAttributionDocument(
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
                if (
                    span.text
                    not in documents[document.document_index].corresponding_spans
                ):
                    documents[document.document_index].corresponding_spans.append(
                        span.text
                    )

    if request.include_spans_in_root is True:
        return {"documents": documents, "spans": spans}
    else:
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

    include_spans_in_root = request.args.get(
        "includeSpansInRoot", type=json.loads, default=False
    )
    return MappedGetAttributionRequest(
        **request.json, index=index, include_spans_in_root=include_spans_in_root
    )
