from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="AttributionRequest")


@_attrs_define
class AttributionRequest:
    """
    Attributes:
        response (str):
        delimiters (Union[Unset, list[str]]): Token IDs that returned spans shouldn't include
        allow_spans_with_partial_words (Union[Unset, bool]): Setting this to False will only check for attributions that
            start and end with a full word Default: False.
        minimum_span_length (Union[Unset, int]): The minimum length to qualify an n-gram span as "interesting" Default:
            1.
        maximum_frequency (Union[Unset, int]): The maximum frequency that an n-gram span can have in an index for us to
            consider it as "interesting" Default: 10.
        maximum_span_density (Union[Unset, float]): The maximum density of spans (measured in number of spans per
            response token) to return in the response Default: 0.05.
        span_ranking_method (Union[Unset, Any]): Ranking method when capping number of spans with maximum_span_density,
            options are 'length' and 'unigram_logprob_sum' Default: 'length'.
        maximum_documents_per_span (Union[Unset, int]): The maximum number of documents to retrieve for each span;
            should be no larger than maximum_frequency Default: 10.
        maximum_context_length (Union[Unset, int]): The maximum number of tokens of the context (on each side) to
            retrieve from the document Default: 250.
        maximum_context_length_long (Union[Unset, int]): The maximum number of tokens of the context (on each side) for
            the document modal Default: 100.
        maximum_context_length_snippet (Union[Unset, int]): The maximum number of tokens of the context (on each side)
            for the snippet in document cards Default: 40.
    """

    response: str
    delimiters: Union[Unset, list[str]] = UNSET
    allow_spans_with_partial_words: Union[Unset, bool] = False
    minimum_span_length: Union[Unset, int] = 1
    maximum_frequency: Union[Unset, int] = 10
    maximum_span_density: Union[Unset, float] = 0.05
    span_ranking_method: Union[Unset, Any] = "length"
    maximum_documents_per_span: Union[Unset, int] = 10
    maximum_context_length: Union[Unset, int] = 250
    maximum_context_length_long: Union[Unset, int] = 100
    maximum_context_length_snippet: Union[Unset, int] = 40
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        response = self.response

        delimiters: Union[Unset, list[str]] = UNSET
        if not isinstance(self.delimiters, Unset):
            delimiters = self.delimiters

        allow_spans_with_partial_words = self.allow_spans_with_partial_words

        minimum_span_length = self.minimum_span_length

        maximum_frequency = self.maximum_frequency

        maximum_span_density = self.maximum_span_density

        span_ranking_method = self.span_ranking_method

        maximum_documents_per_span = self.maximum_documents_per_span

        maximum_context_length = self.maximum_context_length

        maximum_context_length_long = self.maximum_context_length_long

        maximum_context_length_snippet = self.maximum_context_length_snippet

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "response": response,
        })
        if delimiters is not UNSET:
            field_dict["delimiters"] = delimiters
        if allow_spans_with_partial_words is not UNSET:
            field_dict["allowSpansWithPartialWords"] = allow_spans_with_partial_words
        if minimum_span_length is not UNSET:
            field_dict["minimumSpanLength"] = minimum_span_length
        if maximum_frequency is not UNSET:
            field_dict["maximumFrequency"] = maximum_frequency
        if maximum_span_density is not UNSET:
            field_dict["maximumSpanDensity"] = maximum_span_density
        if span_ranking_method is not UNSET:
            field_dict["spanRankingMethod"] = span_ranking_method
        if maximum_documents_per_span is not UNSET:
            field_dict["maximumDocumentsPerSpan"] = maximum_documents_per_span
        if maximum_context_length is not UNSET:
            field_dict["maximumContextLength"] = maximum_context_length
        if maximum_context_length_long is not UNSET:
            field_dict["maximumContextLengthLong"] = maximum_context_length_long
        if maximum_context_length_snippet is not UNSET:
            field_dict["maximumContextLengthSnippet"] = maximum_context_length_snippet

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: dict[str, Any]) -> T:
        d = src_dict.copy()
        response = d.pop("response")

        delimiters = cast(list[str], d.pop("delimiters", UNSET))

        allow_spans_with_partial_words = d.pop("allowSpansWithPartialWords", UNSET)

        minimum_span_length = d.pop("minimumSpanLength", UNSET)

        maximum_frequency = d.pop("maximumFrequency", UNSET)

        maximum_span_density = d.pop("maximumSpanDensity", UNSET)

        span_ranking_method = d.pop("spanRankingMethod", UNSET)

        maximum_documents_per_span = d.pop("maximumDocumentsPerSpan", UNSET)

        maximum_context_length = d.pop("maximumContextLength", UNSET)

        maximum_context_length_long = d.pop("maximumContextLengthLong", UNSET)

        maximum_context_length_snippet = d.pop("maximumContextLengthSnippet", UNSET)

        attribution_request = cls(
            response=response,
            delimiters=delimiters,
            allow_spans_with_partial_words=allow_spans_with_partial_words,
            minimum_span_length=minimum_span_length,
            maximum_frequency=maximum_frequency,
            maximum_span_density=maximum_span_density,
            span_ranking_method=span_ranking_method,
            maximum_documents_per_span=maximum_documents_per_span,
            maximum_context_length=maximum_context_length,
            maximum_context_length_long=maximum_context_length_long,
            maximum_context_length_snippet=maximum_context_length_snippet,
        )

        attribution_request.additional_properties = d
        return attribution_request

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
