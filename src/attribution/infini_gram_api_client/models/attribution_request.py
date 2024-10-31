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

    prompt: str
    response: str
    delimiters: Union[Unset, List[str]] = UNSET
    allow_spans_with_partial_words: Union[Unset, bool] = False
    minimum_span_length: Union[Unset, int] = 1
    maximum_frequency: Union[Unset, int] = 10
    maximum_span_density: Union[Unset, float] = 0.05
    span_ranking_method: Union[Unset, str] = "length"
    include_documents: Union[Unset, bool] = False
    maximum_document_display_length: Union[Unset, int] = 100
    maximum_documents_per_span: Union[Unset, int] = 10
    filter_method: Union[Unset, str] = "none"
    filter_bm_25_fields_considered: Union[Unset, str] = "response"
    filter_bm_25_ratio_to_keep: Union[Unset, float] = 1.0
    include_input_as_tokens: Union[Unset, bool] = False
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        prompt = self.prompt
        response = self.response

        delimiters: Union[Unset, List[str]] = UNSET
        if not isinstance(self.delimiters, Unset):
            delimiters = self.delimiters

        allow_spans_with_partial_words = self.allow_spans_with_partial_words

        minimum_span_length = self.minimum_span_length

        maximum_frequency = self.maximum_frequency

        maximum_span_density = self.maximum_span_density

        span_ranking_method = self.span_ranking_method

        include_documents = self.include_documents

        maximum_document_display_length = self.maximum_document_display_length

        maximum_documents_per_span = self.maximum_documents_per_span

        filter_method = self.filter_method

        filter_bm_25_fields_considered = self.filter_bm_25_fields_considered

        filter_bm_25_ratio_to_keep = self.filter_bm_25_ratio_to_keep

        include_input_as_tokens = self.include_input_as_tokens

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "prompt": prompt,
                "response": response,
            }
        )
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
        if include_documents is not UNSET:
            field_dict["includeDocuments"] = include_documents
        if maximum_document_display_length is not UNSET:
            field_dict["maximumDocumentDisplayLength"] = maximum_document_display_length
        if maximum_documents_per_span is not UNSET:
            field_dict["maximumDocumentsPerSpan"] = maximum_documents_per_span
        if filter_method is not UNSET:
            field_dict["filterMethod"] = filter_method
        if filter_bm_25_fields_considered is not UNSET:
            field_dict["filterBm25FieldsConsidered"] = filter_bm_25_fields_considered
        if filter_bm_25_ratio_to_keep is not UNSET:
            field_dict["filterBm25RatioToKeep"] = filter_bm_25_ratio_to_keep
        if include_input_as_tokens is not UNSET:
            field_dict["includeInputAsTokens"] = include_input_as_tokens

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        prompt = d.pop("prompt")

        response = d.pop("response")

        delimiters = cast(List[str], d.pop("delimiters", UNSET))

        allow_spans_with_partial_words = d.pop("allowSpansWithPartialWords", UNSET)

        minimum_span_length = d.pop("minimumSpanLength", UNSET)

        maximum_frequency = d.pop("maximumFrequency", UNSET)

        maximum_span_density = d.pop("maximumSpanDensity", UNSET)

        span_ranking_method = d.pop("spanRankingMethod", UNSET)

        include_documents = d.pop("includeDocuments", UNSET)

        maximum_document_display_length = d.pop("maximumDocumentDisplayLength", UNSET)

        maximum_documents_per_span = d.pop("maximumDocumentsPerSpan", UNSET)

        filter_method = d.pop("filterMethod", UNSET)

        filter_bm_25_fields_considered = d.pop("filterBm25FieldsConsidered", UNSET)

        filter_bm_25_ratio_to_keep = d.pop("filterBm25RatioToKeep", UNSET)

        include_input_as_tokens = d.pop("includeInputAsTokens", UNSET)

        attribution_request = cls(
            prompt=prompt,
            response=response,
            delimiters=delimiters,
            allow_spans_with_partial_words=allow_spans_with_partial_words,
            minimum_span_length=minimum_span_length,
            maximum_frequency=maximum_frequency,
            maximum_span_density=maximum_span_density,
            span_ranking_method=span_ranking_method,
            include_documents=include_documents,
            maximum_document_display_length=maximum_document_display_length,
            maximum_documents_per_span=maximum_documents_per_span,
            filter_method=filter_method,
            filter_bm25_fields_considered=filter_bm_25_fields_considered,
            filter_bm_25_ratio_to_keep=filter_bm_25_ratio_to_keep,
            include_input_as_tokens=include_input_as_tokens,
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
