from dataclasses import dataclass, field
from itertools import islice
from operator import itemgetter
from typing import Iterable, List, Optional, Sequence, cast

from flask import json, request
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
from src.attribution.infini_gram_api_client.models.document_with_pointer_metadata import (
    DocumentWithPointerMetadata,
)
from src.attribution.infini_gram_api_client.models.http_validation_error import (
    HTTPValidationError,
)
from src.config import cfg

from .infini_gram_api_client import Client


@dataclass
class ResponseAttributionDocument:
    text: str
    corresponding_spans: List[int]
    corresponding_span_texts: List[str]
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
class FlattenedSpanDocument:
    document_index: int
    document_length: int
    display_length: int
    metadata: DocumentWithPointerMetadata
    token_ids: List[int]
    text: str
    span_text: str


@dataclass
class FlattenedSpan:
    text: str
    left: int
    right: int
    nested_spans: Iterable[AttributionSpanWithDocuments]
    documents: List[FlattenedSpanDocument]


def flatten_spans(
    spans: Sequence[AttributionSpanWithDocuments],
    input_tokens: Iterable[str],
) -> List[FlattenedSpan]:
    # We're sorting by left position here first because that helps clean up some edge cases that happen if we only sort by length
    # Sorting by length lets us reduce the number of loops we do math in and removes the need to account for double-nested spans
    spans_sorted_by_left_position_then_length = sorted(
        spans,
        key=lambda span: (span.left, span.length),
    )

    top_level_spans: List[FlattenedSpan] = []
    spans_already_nested: List[int] = []

    # starting from the first span in the text (lowest left value), check to see if any spans overlap it or are inside it
    for i, span in enumerate(spans_sorted_by_left_position_then_length):
        if i in spans_already_nested:
            continue

        left = span.left
        right = span.right
        overlapping_spans: List[AttributionSpanWithDocuments] = []

        next_index = i + 1
        for j, span_to_check in enumerate(
            iterable=islice(
                spans_sorted_by_left_position_then_length, next_index, None
            ),
            start=next_index,
        ):
            if (
                left <= span_to_check.left < right
                or left <= span_to_check.right < right
            ):
                spans_already_nested.append(j)
                overlapping_spans.append(span_to_check)
                left = min(span_to_check.left, left)
                right = max(span_to_check.right, right)

        new_documents = [
            FlattenedSpanDocument(
                document_index=document.document_index,
                document_length=document.document_length,
                display_length=document.display_length,
                metadata=document.metadata,
                token_ids=document.token_ids,
                text=document.text,
                span_text=overlapping_span.text,
            )
            for overlapping_span in overlapping_spans
            for document in overlapping_span.documents
        ]

        text = "".join(islice(input_tokens, left, right))

        if len(overlapping_spans) > 0:
            top_level_spans.append(
                FlattenedSpan(
                    text,
                    left=left,
                    right=right,
                    documents=new_documents,
                    nested_spans=overlapping_spans,
                )
            )

    return top_level_spans


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
            include_input_as_tokens=True,
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

    if attribution_response.input_tokens is None:
        raise exceptions.BadGateway(
            description="The version of infinigram-api we hit doesn't support or didn't return input_tokens"
        )

    collapsed_spans = flatten_spans(
        input_tokens=attribution_response.input_tokens,
        spans=cast(List[AttributionSpanWithDocuments], attribution_response.spans),
    )

    documents: dict[int, ResponseAttributionDocument] = {}
    spans: dict[int, ResponseAttributionSpan] = {}
    for span_index, span in enumerate(collapsed_spans):
        if spans.get(span_index) is None:
            spans[span_index] = ResponseAttributionSpan(text=span.text)

        for document in span.documents:
            if document.document_index not in spans[span_index].documents:
                spans[span_index].documents.append(document.document_index)

            if documents.get(document.document_index) is None:
                documents[document.document_index] = ResponseAttributionDocument(
                    text=document.text,
                    corresponding_spans=[span_index],
                    corresponding_span_texts=[document.span_text],
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
                    span_index
                    not in documents[document.document_index].corresponding_spans
                ):
                    documents[document.document_index].corresponding_spans.append(
                        span_index
                    )

    if request.include_spans_in_root is True:
        return {"documents": documents, "spans": spans}
    else:
        # If we get more documents back than the requestor wants, sort them by their corresponding span count and return the top X
        if len(documents) > request.max_documents:
            sorted_documents = sorted(
                [
                    (id, len(document.corresponding_spans))
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
