from copy import deepcopy
from typing import cast

from opentelemetry import trace
from rank_bm25 import BM25Okapi  # type: ignore

from api.attribution.flatten_spans import flatten_spans
from api.attribution.models.document import (
    AttributionDocumentSnippet,
    ResponseAttributionDocument,
)
from api.attribution.models.intermediate import FlattenedSpanDocument, IntermediateAttributionDocument
from api.attribution.models.request import AttributionRequest
from api.attribution.models.response import AttributionResponse
from api.attribution.models.span import TopLevelAttributionSpan
from core.pii.does_contain_pii import does_contain_pii
from infini_gram_api_client.models import AttributionResponse as InfiniGramAttributionResponse
from infini_gram_api_client.models.attribution_document import AttributionDocument
from infini_gram_api_client.models.attribution_span import AttributionSpan
from infini_gram_api_client.models.available_infini_gram_index_id import (
    AvailableInfiniGramIndexId,
)

tracer = trace.get_tracer(__name__)


@tracer.start_as_current_span("Attribution/process_attribution")
def process_attribution(
    infini_gram_response: InfiniGramAttributionResponse,
    request: AttributionRequest,
    index: AvailableInfiniGramIndexId,
) -> AttributionResponse:
    # This is mostly for type checking, as this should be checked calling this function
    if infini_gram_response.input_tokens is None:
        no_attribution_input_tokens = "AttributionResponse input_tokens cannot be None"
        raise ValueError(no_attribution_input_tokens)

    filtered_spans = filter_span_documents(spans=infini_gram_response.spans)

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
        input_tokens=infini_gram_response.input_tokens,
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
