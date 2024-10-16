from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="AttributionRequest")


@_attrs_define
class AttributionRequest:
    """
    Attributes:
        query (str):
        delimiters (Union[Unset, List[str]]): Token IDs that returned spans shouldn't include
        maximum_span_density (Union[Unset, float]): The maximum density of spans (measured in number of spans per
            response token) to return in the response Default: 0.05.
        minimum_span_length (Union[Unset, int]): The minimum length to qualify an n-gram span as "interesting" Default:
            5.
        maximum_frequency (Union[Unset, int]): The maximum frequency that an n-gram span can have in an index for us to
            consider it as "interesting" Default: 10.
        include_documents (Union[Unset, bool]): Set this to True if you want to have the response include referenced
            documents along with the spans Default: False.
        maximum_document_display_length (Union[Unset, int]): The maximum length in tokens of the returned document text
            Default: 100.
        include_input_as_tokens (Union[Unset, bool]): Set this to True if you want the response to include the input
            string as a list of string tokens Default: False.
        allow_spans_with_partial_words (Union[Unset, bool]): Setting this to False will only check for attributions that
            start and end with a full word Default: False.
        filter_method (Union[Unset, str]): Filtering method for post-processing the retrieved documents, options are
            'none', 'bm25' Default: 'none'.
        filter_bm_25_ratio_to_keep (Union[Unset, float]): The ratio of documents to keep after filtering with BM25
            Default: 1.0.
    """

    query: str
    delimiters: Union[Unset, List[str]] = UNSET
    maximum_span_density: Union[Unset, float] = 0.05
    minimum_span_length: Union[Unset, int] = 5
    maximum_frequency: Union[Unset, int] = 10
    include_documents: Union[Unset, bool] = False
    maximum_document_display_length: Union[Unset, int] = 100
    include_input_as_tokens: Union[Unset, bool] = False
    allow_spans_with_partial_words: Union[Unset, bool] = False
    filter_method: Union[Unset, str] = "none"
    filter_bm_25_ratio_to_keep: Union[Unset, float] = 1.0
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        query = self.query

        delimiters: Union[Unset, List[str]] = UNSET
        if not isinstance(self.delimiters, Unset):
            delimiters = self.delimiters

        maximum_span_density = self.maximum_span_density

        minimum_span_length = self.minimum_span_length

        maximum_frequency = self.maximum_frequency

        include_documents = self.include_documents

        maximum_document_display_length = self.maximum_document_display_length

        include_input_as_tokens = self.include_input_as_tokens

        allow_spans_with_partial_words = self.allow_spans_with_partial_words

        filter_method = self.filter_method

        filter_bm_25_ratio_to_keep = self.filter_bm_25_ratio_to_keep

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if delimiters is not UNSET:
            field_dict["delimiters"] = delimiters
        if maximum_span_density is not UNSET:
            field_dict["maximumSpanDensity"] = maximum_span_density
        if minimum_span_length is not UNSET:
            field_dict["minimumSpanLength"] = minimum_span_length
        if maximum_frequency is not UNSET:
            field_dict["maximumFrequency"] = maximum_frequency
        if include_documents is not UNSET:
            field_dict["includeDocuments"] = include_documents
        if maximum_document_display_length is not UNSET:
            field_dict["maximumDocumentDisplayLength"] = maximum_document_display_length
        if include_input_as_tokens is not UNSET:
            field_dict["includeInputAsTokens"] = include_input_as_tokens
        if allow_spans_with_partial_words is not UNSET:
            field_dict["allowSpansWithPartialWords"] = allow_spans_with_partial_words
        if filter_method is not UNSET:
            field_dict["filterMethod"] = filter_method
        if filter_bm_25_ratio_to_keep is not UNSET:
            field_dict["filterBm25RatioToKeep"] = filter_bm_25_ratio_to_keep

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        query = d.pop("query")

        delimiters = cast(List[str], d.pop("delimiters", UNSET))

        maximum_span_density = d.pop("maximumSpanDensity", UNSET)

        minimum_span_length = d.pop("minimumSpanLength", UNSET)

        maximum_frequency = d.pop("maximumFrequency", UNSET)

        include_documents = d.pop("includeDocuments", UNSET)

        maximum_document_display_length = d.pop("maximumDocumentDisplayLength", UNSET)

        include_input_as_tokens = d.pop("includeInputAsTokens", UNSET)

        allow_spans_with_partial_words = d.pop("allowSpansWithPartialWords", UNSET)

        filter_method = d.pop("filterMethod", UNSET)

        filter_bm_25_ratio_to_keep = d.pop("filterBm25RatioToKeep", UNSET)

        attribution_request = cls(
            query=query,
            delimiters=delimiters,
            maximum_span_density=maximum_span_density,
            minimum_span_length=minimum_span_length,
            maximum_frequency=maximum_frequency,
            include_documents=include_documents,
            maximum_document_display_length=maximum_document_display_length,
            include_input_as_tokens=include_input_as_tokens,
            allow_spans_with_partial_words=allow_spans_with_partial_words,
            filter_method=filter_method,
            filter_bm_25_ratio_to_keep=filter_bm_25_ratio_to_keep,
        )

        attribution_request.additional_properties = d
        return attribution_request

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
