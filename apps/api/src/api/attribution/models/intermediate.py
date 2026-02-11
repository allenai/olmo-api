from dataclasses import dataclass

from infini_gram_api_client.models.attribution_document_metadata import (
    AttributionDocumentMetadata,
)
from infini_gram_api_client.models.attribution_span import (
    AttributionSpan,
)


@dataclass(kw_only=True)
class IntermediateAttributionDocument:
    document_index: int
    document_length: int
    display_length: int
    needle_offset: int
    metadata: AttributionDocumentMetadata
    token_ids: list[int]
    text: str
    display_length_long: int
    needle_offset_long: int
    text_long: str
    display_offset_snippet: int
    needle_offset_snippet: int
    text_snippet: str
    relevance_score: float


@dataclass(kw_only=True)
class FlattenedSpanDocument(IntermediateAttributionDocument):
    span_text: str


@dataclass(kw_only=True)
class FlattenedSpan:
    text: str
    left: int
    right: int
    nested_spans: list[AttributionSpan]
    documents: list[FlattenedSpanDocument]
