from typing import TYPE_CHECKING

from api.attribution.models.intermediate import FlattenedSpanDocument
from api.attribution.sources import INFINI_GRAM_SOURCES
from core import APIInterface

if TYPE_CHECKING:
    from typing import Self


class AttributionDocumentSnippet(APIInterface):
    text: str
    corresponding_span_text: str


class ResponseAttributionDocument(APIInterface):
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

        source_detail = INFINI_GRAM_SOURCES.get(source, None)

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
