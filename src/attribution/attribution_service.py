from dataclasses import dataclass, field
from typing import Annotated, List, Optional, Self, cast

from pydantic import AfterValidator, Field
from werkzeug import exceptions
from rank_bm25 import BM25Okapi  # type: ignore

from src.api_interface import APIInterface
from src.attribution.infini_gram_api_client.api.default import (
    get_document_attributions_index_attribution_post,
)
from src.attribution.infini_gram_api_client.errors import UnexpectedStatus
from src.attribution.infini_gram_api_client.models.attribution_request import (
    AttributionRequest,
)
from src.attribution.infini_gram_api_client.models.attribution_span import (
    AttributionSpan,
)
from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import (
    AvailableInfiniGramIndexId,
)
from src.attribution.infini_gram_api_client.models.http_validation_error import (
    HTTPValidationError,
)
from src.config import cfg
from src.util.pii_regex import does_contain_pii

from .flatten_spans import (
    FlattenedSpan,
    FlattenedSpanDocument,
    flatten_spans,
    IntermediateAttributionDocument,
)
from .infini_gram_api_client import Client


@dataclass
class AttributionDocumentSnippet:
    text: str
    corresponding_span_text: str


@dataclass
class ResponseAttributionDocument:
    text_long: str
    snippets: list[AttributionDocumentSnippet]
    corresponding_spans: List[int]
    corresponding_span_texts: List[str]
    index: str
    source: str
    relevance_score: float
    title: Optional[str] = None
    url: Optional[str] = None

    @classmethod
    def from_flattened_span_document(
        cls, document: FlattenedSpanDocument, span_index: int
    ) -> Self:
        metadata = document.metadata.additional_properties.get("metadata", {})
        if "metadata" in metadata:
            url = metadata["metadata"].get("url", None)
        elif "doc" in metadata:
            url = metadata["doc"].get("url", None)
        else:
            url = None

        source = document.metadata.additional_properties.get("path", "").split("/")[0]
        if source not in [
            "arxiv",
            "algebraic-stack",
            "open-web-math",
            "pes2o",
            "starcoder",
            "wiki",
            "dolmino",
        ]:
            source = metadata.get("source", None)

        return cls(
            text_long=document.text_long,
            snippets=[
                AttributionDocumentSnippet(
                    text=document.text_snippet, corresponding_span_text=document.span_text
                )
            ],
            corresponding_spans=[span_index],
            corresponding_span_texts=[document.span_text],
            index=str(document.document_index),
            source=source,
            relevance_score=document.relevance_score,
            title=document.metadata.additional_properties.get("metadata", {})
            .get("metadata", {})
            .get("title", None),
            url=url,
        )


def model_id_is_valid_for_infini_gram(model_id: str) -> str:
    valid_model_ids = list(cfg.infini_gram.model_index_map.keys())
    if model_id not in valid_model_ids:
        raise ValueError(f"{model_id} must be one of {valid_model_ids}")

    return model_id


def should_block_prompt(prompt: str) -> str:
    if "lyric" in prompt.lower():
        raise ValueError("The prompt is blocked due to legal compliance.")
    return prompt


class GetAttributionRequest(APIInterface):
    prompt: Annotated[str, AfterValidator(should_block_prompt)]
    model_response: str
    model_id: Annotated[str, AfterValidator(model_id_is_valid_for_infini_gram)]
    max_documents: int = Field(default=10)  # unused
    max_display_context_length: int = Field(default=100)


@dataclass
class ResponseAttributionSpan:
    text: str
    documents: List[int] = field(default_factory=lambda: [])


@dataclass
class TopLevelAttributionSpan(ResponseAttributionSpan):
    nested_spans: List[ResponseAttributionSpan] = field(default_factory=lambda: [])

    @classmethod
    def from_flattened_span(cls, span: FlattenedSpan) -> Self:
        return cls(
            text=span.text,
            nested_spans=[
                ResponseAttributionSpan(
                    text=nested_span.text,
                    documents=[
                        document.document_index for document in nested_span.documents
                    ],
                )
                for nested_span in span.nested_spans
            ],
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

    if not any(
        snippet.text == new_document.text_snippet for snippet in mapped_document.snippets
    ):
        mapped_document.snippets.append(
            AttributionDocumentSnippet(
                text=new_document.text_snippet, corresponding_span_text=new_document.span_text
            )
        )


def should_block_request(request: GetAttributionRequest) -> bool:
    if "lyric" in request.prompt.lower():
        return True
    return False


def get_attribution(
    request: GetAttributionRequest,
    infini_gram_client: Client,
):
    index = AvailableInfiniGramIndexId(
        cfg.infini_gram.model_index_map[request.model_id]
    )

    if should_block_request(request):
        raise exceptions.Forbidden(
            description="The request was blocked by due to legal compliance."
        )

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
        raise exceptions.BadGateway(
            f"Something went wrong when calling the infini-gram API: {e.status_code} {e.content.decode()}"
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

    # populate BM25 relevance scores; truncate excessive context
    docs = [doc.text for span in attribution_response.spans for doc in span.documents]
    if len(docs) > 0:
        tokenized_corpus = [doc.split(" ") for doc in docs]
        bm25 = BM25Okapi(tokenized_corpus)
        doc_scores = bm25.get_scores((request.prompt + " " + request.model_response).split(" "))
        i = 0
        for span in attribution_response.spans:
            for j in range(len(span.documents)):
                doc = span.documents[j]
                span.documents[j] = IntermediateAttributionDocument(
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
        spans=cast(List[AttributionSpan], attribution_response.spans),
    )

    mapped_documents: dict[int, ResponseAttributionDocument] = {}
    mapped_spans: dict[int, ResponseAttributionSpan] = {}

    for span_index, span in enumerate(flattened_spans):
        if span_index not in mapped_spans:
            mapped_spans[span_index] = TopLevelAttributionSpan.from_flattened_span(span)

        for current_span_document in span.documents:
            if does_contain_pii(current_span_document.text_long):
                continue

            if (
                current_span_document.document_index
                not in mapped_spans[span_index].documents
            ):
                mapped_spans[span_index].documents.append(
                    current_span_document.document_index
                )

            if current_span_document.document_index not in mapped_documents:
                mapped_documents[current_span_document.document_index] = (
                    ResponseAttributionDocument.from_flattened_span_document(
                        current_span_document, span_index
                    )
                )
            else:
                update_mapped_document(
                    # We make sure the mapped_document is present in the if corresponding to this else
                    mapped_documents.get(current_span_document.document_index),  # type: ignore [arg-type]
                    span_text=span.text,
                    new_document=current_span_document,
                    span_index=span_index,
                )

    return {
        "index": index,
        "documents": sorted(
            mapped_documents.values(),
            key=lambda document: document.relevance_score,
            reverse=True,
        ),
        "spans": list(mapped_spans.values()),
    }
