from dataclasses import dataclass, field
from typing import List, Optional, cast

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
from src.attribution.infini_gram_api_client.models.http_validation_error import (
    HTTPValidationError,
)
from src.config import cfg

from .flatten_spans import flatten_spans
from .infini_gram_api_client import Client


@dataclass
class ResponseAttributionDocument:
    text: str
    corresponding_spans: List[int]
    corresponding_span_texts: List[str]
    index: str
    source: str
    title: Optional[str]
    url: Optional[str]


class GetAttributionRequest(APIInterface):
    model_response: str
    model_id: str
    max_documents: int = 10


class MappedGetAttributionRequest(GetAttributionRequest):
    index: AvailableInfiniGramIndexId
    spans_and_documents_as_list: bool


@dataclass
class ResponseAttributionSpan:
    text: str
    documents: List[int] = field(default_factory=lambda: [])


@dataclass
class TopLevelAttributionSpan(ResponseAttributionSpan):
    nested_spans: List[ResponseAttributionSpan] = field(default_factory=lambda: [])


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
            maximum_span_density=0.05,
            minimum_span_length=1,
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
            spans[span_index] = TopLevelAttributionSpan(
                text=span.text,
                nested_spans=[
                    ResponseAttributionSpan(
                        text=nested_span.text,
                        documents=[
                            document.document_index
                            for document in nested_span.documents
                        ],
                    )
                    for nested_span in span.nested_spans
                ],
            )

        for document in span.documents:
            if document.document_index not in spans[span_index].documents:
                spans[span_index].documents.append(document.document_index)

            if documents.get(document.document_index) is None:
                metadata = document.metadata.additional_properties.get("metadata", {})
                if "metadata" in metadata:
                    url = metadata["metadata"].get("url", None)
                elif "doc" in metadata:
                    url = metadata["doc"].get("url", None)
                else:
                    url = None
                source = document.metadata.additional_properties.get("path", "").split("/")[0]
                if source not in ["arxiv", "algebraic-stack", "open-web-math", "pes2o", "starcoder", "wiki"]:
                    source = metadata.get("source", None)
                    if source == "dclm-hero-run-fasttext_for_HF":
                        source = "dclm"

                documents[document.document_index] = ResponseAttributionDocument(
                    text=document.text,
                    corresponding_spans=[span_index],
                    corresponding_span_texts=[document.span_text],
                    index=str(document.document_index),
                    source=source,
                    title=metadata.get("metadata", {}).get("title", None),
                    url=url,
                )
            else:
                if (
                    span_index
                    not in documents[document.document_index].corresponding_spans
                ):
                    documents[document.document_index].corresponding_spans.append(
                        span_index
                    )

                if (
                    document.span_text
                    not in documents[document.document_index].corresponding_span_texts
                ):
                    documents[document.document_index].corresponding_span_texts.append(
                        document.span_text
                    )
    if request.spans_and_documents_as_list is True:
        return {"documents": list(documents.values()), "spans": list(spans.values())}
    else:
        return {"documents": documents, "spans": spans}



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

    spans_and_documents_as_list = request.args.get(
        "spansAndDocumentsAsList", type=json.loads, default=False
    )

    return MappedGetAttributionRequest(**request.json, index=index, spans_and_documents_as_list = spans_and_documents_as_list)
