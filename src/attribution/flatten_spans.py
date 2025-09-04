from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import islice

from pydantic import BaseModel

from src.attribution.infini_gram_api_client.models.attribution_document import AttributionDocument
from src.attribution.infini_gram_api_client.models.attribution_span import (
    AttributionSpan,
)


class IntermediateAttributionDocument(BaseModel, AttributionDocument):
    relevance_score: float


class IntermediateAttributionSpan(BaseModel, AttributionSpan):
    intermediate_documents: list[IntermediateAttributionDocument]


@dataclass
class FlattenedSpanDocument(IntermediateAttributionDocument):
    span_text: str


@dataclass
class FlattenedSpan:
    text: str
    left: int
    right: int
    nested_spans: list[IntermediateAttributionSpan]
    documents: list[FlattenedSpanDocument]


def flatten_spans(
    spans: Sequence[IntermediateAttributionSpan],
    input_tokens: Iterable[str],
) -> list[FlattenedSpan]:
    # We're sorting by left position here first because that helps clean up some edge cases that happen if we only sort by length
    # Sorting by length lets us reduce the number of loops we do math in and (i think) removes the need to account for double-nested spans
    spans_sorted_by_left_position_then_length = sorted(
        spans,
        key=lambda span: (span.left, span.length),
    )

    top_level_spans: list[FlattenedSpan] = []
    spans_already_nested: list[int] = []

    # starting from the first span in the text (lowest left value), check to see if any spans overlap it or are inside it
    for i, span in enumerate(spans_sorted_by_left_position_then_length):
        # If a span has been accounted for as a nested span we don't want to do any more nesting
        if i in spans_already_nested:
            continue

        left = span.left
        right = span.right
        # This span is a nested span for the top level span, even if there's nothing else under it.
        nested_spans: list[IntermediateAttributionSpan] = [span]

        next_index = i + 1
        for j, span_to_check in enumerate(
            # check for nested spans that come after this one in the list
            iterable=islice(spans_sorted_by_left_position_then_length, next_index, None),
            start=next_index,
        ):
            if j in spans_already_nested:
                continue

            if left <= span_to_check.left < right or left <= span_to_check.right < right:
                spans_already_nested.append(j)
                nested_spans.append(span_to_check)

                # Migrating the left/right to account for the new span lets us catch any spans that can be nested under any of the spans inside the new top-level span
                left = min(span_to_check.left, left)
                right = max(span_to_check.right, right)

        flattened_span_documents = [
            FlattenedSpanDocument(  # type: ignore
                document_index=document.document_index,
                document_length=document.document_length,
                display_length=document.display_length,
                needle_offset=document.needle_offset,
                metadata=document.metadata,
                token_ids=document.token_ids,
                text=document.text,
                display_length_long=document.display_length_long,
                needle_offset_long=document.needle_offset_long,
                text_long=document.text_long,
                display_offset_snippet=document.display_offset_snippet,
                needle_offset_snippet=document.needle_offset_snippet,
                text_snippet=document.text_snippet,
                # we add relevance_score in the intermediate document
                relevance_score=document.relevance_score,
                span_text=overlapping_span.text,
            )
            for overlapping_span in nested_spans
            for document in overlapping_span.intermediate_documents
        ]

        text = "".join(islice(input_tokens, left, right))

        top_level_spans.append(
            FlattenedSpan(
                text,
                left=left,
                right=right,
                documents=flattened_span_documents,
                nested_spans=nested_spans,
            )
        )

    return top_level_spans
