from dataclasses import dataclass
from itertools import islice
from typing import Iterable, List, Sequence

from src.attribution.infini_gram_api_client.models.attribution_span_with_documents import (
    AttributionSpanWithDocuments,
)
from src.attribution.infini_gram_api_client.models.document_with_pointer_metadata import (
    DocumentWithPointerMetadata,
)


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
        overlapping_spans: List[AttributionSpanWithDocuments] = [span]

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
