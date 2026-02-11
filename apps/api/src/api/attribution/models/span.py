from pydantic import Field

from api.attribution.models.intermediate import FlattenedSpan
from core import APIInterface


class ResponseAttributionSpan(APIInterface):
    text: str
    start_index: int
    documents: list[int] = Field(default_factory=list)


class TopLevelAttributionSpan(ResponseAttributionSpan):
    nested_spans: list[ResponseAttributionSpan] = Field(default_factory=list)

    @classmethod
    def from_flattened_span(cls, span: FlattenedSpan) -> "TopLevelAttributionSpan":
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
