from copy import deepcopy
from dataclasses import field
from typing import Annotated, Self, cast

from flask import current_app
from groq import BaseModel
from pydantic import AfterValidator, Field
from rank_bm25 import BM25Okapi  # type: ignore
from werkzeug import exceptions

from src.api_interface import APIInterface
from src.attribution.infini_gram_api_client.api.default import (
    get_document_attributions_index_attribution_post,
)
from src.attribution.infini_gram_api_client.errors import UnexpectedStatus
from src.attribution.infini_gram_api_client.models.attribution_document import (
    AttributionDocument,
)
from src.attribution.infini_gram_api_client.models.attribution_request import (
    AttributionRequest,
)
from src.attribution.infini_gram_api_client.models.attribution_span import (
    AttributionSpan,
)
from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import (
    AvailableInfiniGramIndexId,
)
from src.attribution.infini_gram_api_client.models.problem import Problem
from src.attribution.infini_gram_api_client.models.request_validation_error import RequestValidationError
from src.config.get_config import cfg
from src.dao.engine_models.model_config import ModelConfig
from src.util.pii_regex import does_contain_pii

from .flatten_spans import (
    FlattenedSpan,
    FlattenedSpanDocument,
    IntermediateAttributionDocument,
    flatten_spans,
)
from .infini_gram_api_client import Client


class AttributionDocumentSnippet(BaseModel):
    text: str
    corresponding_span_text: str


class ResponseAttributionDocument(BaseModel):
    text_long: str
    snippets: list[AttributionDocumentSnippet]
    corresponding_spans: list[int]
    corresponding_span_texts: list[str]
    index: str
    source: str | None
    usage: str | None
    display_name: str | None
    source_url: str | None
    relevance_score: float
    title: str | None = None
    url: str | None = None
    secondary_name: str | None = None

    @classmethod
    def from_flattened_span_document(cls, document: FlattenedSpanDocument, span_index: int) -> Self:
        metadata = document.metadata.additional_properties.get("metadata", {})
        if "metadata" in metadata:
            url = metadata["metadata"].get("url", None)
        elif "doc" in metadata:
            url = metadata["doc"].get("url", None)
        else:
            url = None

        source = document.metadata.additional_properties.get("path", "").split("/")[0]
        if source not in {
            "arxiv",
            "algebraic-stack",
            "open-web-math",
            "pes2o",
            "starcoder",
            "wiki",
            "dolmino",
        }:
            source = metadata.get("source", None)

        source_detail = cfg.infini_gram.source_map.get(source, None)

        return cls(
            text_long=document.text_long,
            snippets=[
                AttributionDocumentSnippet(
                    text=document.text_snippet,
                    corresponding_span_text=document.span_text,
                )
            ],
            corresponding_spans=[span_index],
            corresponding_span_texts=[document.span_text],
            index=str(document.document_index),
            source=source,
            usage=source_detail.usage if source_detail is not None else None,
            display_name=source_detail.display_name if source_detail is not None else None,
            source_url=source_detail.url if source_detail is not None else None,
            relevance_score=document.relevance_score,
            title=document.metadata.additional_properties.get("metadata", {}).get("metadata", {}).get("title", None),
            url=url,
            secondary_name=source_detail.secondary_name if source_detail is not None else None,
        )


def should_block_prompt(prompt: str) -> str:
    if "lyric" in prompt.lower() or "song" in prompt.lower():
        msg = "The prompt is blocked due to legal compliance."
        raise ValueError(msg)
    return prompt


class GetAttributionRequest(APIInterface):
    prompt: Annotated[str, AfterValidator(should_block_prompt)]
    model_response: str
    model_id: str
    max_documents: int = Field(default=10)  # unused
    max_display_context_length: int = Field(default=250)


class ResponseAttributionSpan(BaseModel):
    text: str
    start_index: int
    documents: list[int] = field(default_factory=list)


class TopLevelAttributionSpan(ResponseAttributionSpan):
    nested_spans: list[ResponseAttributionSpan] = field(default_factory=list)

    @staticmethod
    def from_flattened_span(span: FlattenedSpan) -> "TopLevelAttributionSpan":
        return TopLevelAttributionSpan(
            text=span.text,
            nested_spans=[
                ResponseAttributionSpan(
                    text=nested_span.text,
                    documents=[document.document_index for document in nested_span.documents],
                    start_index=nested_span.left,
                )
                for nested_span in span.nested_spans
            ],
            start_index=span.left,
        )


def update_mapped_document(
    mapped_document: ResponseAttributionDocument,
    span_index: int,
    span_text: str,
    new_document: FlattenedSpanDocument,
):
    if span_index not in mapped_document.corresponding_spans:
        mapped_document.corresponding_spans.append(span_index)

    if span_text not in mapped_document.corresponding_span_texts:
        mapped_document.corresponding_span_texts.append(span_text)

    if not any(snippet.text == new_document.text_snippet for snippet in mapped_document.snippets):
        mapped_document.snippets.append(
            AttributionDocumentSnippet(
                text=new_document.text_snippet,
                corresponding_span_text=new_document.span_text,
            )
        )


class AttributionResponse(BaseModel):
    index: str
    documents: list[ResponseAttributionDocument]
    spans: list[TopLevelAttributionSpan]


def get_attribution(request: GetAttributionRequest, infini_gram_client: Client, model_config: ModelConfig):
    index = AvailableInfiniGramIndexId(model_config.infini_gram_index)

    try:
        attribution_response = get_document_attributions_index_attribution_post.sync(
            index=index,
            client=infini_gram_client,
            body=AttributionRequest(
                response=request.model_response,
                delimiters=["\n", "."],
                allow_spans_with_partial_words=False,
                minimum_span_length=1,
                maximum_frequency=1000000,
                maximum_span_density=0.05,
                span_ranking_method="unigram_logprob_sum",
                maximum_context_length=max(250, request.max_display_context_length),
                maximum_context_length_long=request.max_display_context_length,
                maximum_context_length_snippet=40,
                maximum_documents_per_span=10,
            ),
        )
    except UnexpectedStatus as e:
        msg = f"Something went wrong when calling the infini-gram API: {e.status_code} {e.content.decode()}"
        raise exceptions.BadGateway(msg) from e

    if isinstance(attribution_response, RequestValidationError):
        current_app.logger.error(
            "Validation error from infini-gram %s, errors %s",
            attribution_response.title,
            str(attribution_response.errors),
        )
        # validation error handling
        raise exceptions.InternalServerError(
            description=f"infini-gram API reported a validation error: {attribution_response.title}\nThis is likely an error in olmo-api."
        )

    if isinstance(attribution_response, Problem):
        current_app.logger.error(
            "Problem from infini-gram %s, detail %s",
            attribution_response.title,
            str(attribution_response.detail),
        )

        if attribution_response.type_ == "server-overloaded":
            raise exceptions.ServiceUnavailable(
                description="OlmoTrace is currently overloaded. Please try again later."
            )

        raise exceptions.InternalServerError(
            description=f"infini-gram API reported an error: {attribution_response.title}"
        )

    if attribution_response is None:
        raise exceptions.BadGateway(description="Something went wrong when calling the infini-gram API")

    if attribution_response.input_tokens is None:
        raise exceptions.BadGateway(
            description="The version of infinigram-api we hit doesn't support or didn't return input_tokens"
        )

    filtered_spans = filter_span_documents(attribution_response.spans)

    # populate BM25 relevance scores; truncate excessive context
    docs = [doc.text for span in filtered_spans for doc in span.documents]
    if len(docs) > 0:
        tokenized_corpus = [doc.split(" ") for doc in docs]
        bm25 = BM25Okapi(tokenized_corpus)
        doc_scores = bm25.get_scores((request.prompt + " " + request.model_response).split(" "))
        i = 0
        for span_to_rank in filtered_spans:
            for j in range(len(span_to_rank.documents)):
                doc = span_to_rank.documents[j]
                span_to_rank.documents[j] = IntermediateAttributionDocument(  # pyright: ignore[reportCallIssue, reportArgumentType]
                    document_index=doc.document_index,
                    document_length=doc.document_length,
                    display_length=doc.display_length,
                    needle_offset=doc.needle_offset,
                    metadata=doc.metadata,
                    token_ids=doc.token_ids,
                    text=doc.text,
                    display_length_long=doc.display_length_long,
                    needle_offset_long=doc.needle_offset_long,
                    text_long=doc.text_long,
                    display_offset_snippet=doc.display_offset_snippet,
                    needle_offset_snippet=doc.needle_offset_snippet,
                    text_snippet=doc.text_snippet,
                    relevance_score=doc_scores[i],
                )
                i += 1

    flattened_spans = flatten_spans(
        input_tokens=attribution_response.input_tokens,
        spans=cast(list[AttributionSpan], filtered_spans),
    )

    mapped_documents: dict[int, ResponseAttributionDocument] = {}
    mapped_spans: dict[int, TopLevelAttributionSpan] = {}

    for span_index, span in enumerate(flattened_spans):
        if span_index not in mapped_spans:
            mapped_spans[span_index] = TopLevelAttributionSpan.from_flattened_span(span)

        for current_span_document in span.documents:
            if does_contain_pii(current_span_document.text_long):
                continue

            if current_span_document.document_index not in mapped_spans[span_index].documents:
                mapped_spans[span_index].documents.append(current_span_document.document_index)

            if current_span_document.document_index not in mapped_documents:
                mapped_documents[current_span_document.document_index] = (
                    ResponseAttributionDocument.from_flattened_span_document(current_span_document, span_index)
                )
            else:
                update_mapped_document(
                    # We make sure the mapped_document is present in the if corresponding to this else
                    mapped_documents.get(current_span_document.document_index),  # type: ignore [arg-type]
                    span_text=span.text,
                    new_document=current_span_document,
                    span_index=span_index,
                )

    return AttributionResponse(
        index=index,
        documents=sorted(
            mapped_documents.values(),
            key=lambda document: document.relevance_score,
            reverse=True,
        ),
        spans=sorted(mapped_spans.values(), key=lambda span: span.start_index),
    )


def filter_document(document: AttributionDocument):
    if document.blocked:
        return False
    return not does_contain_pii(document.text_long)


def filter_span_documents(spans: list[AttributionSpan]):
    copied_spans = deepcopy(spans)

    for span in copied_spans:
        filtered_documents = list(filter(filter_document, span.documents))
        span.documents = filtered_documents

    return list(filter(lambda span: len(span.documents) > 0, copied_spans))
