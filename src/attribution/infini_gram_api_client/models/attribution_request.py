from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="AttributionRequest")


@_attrs_define
class AttributionRequest:
    """
    Attributes:
        prompt (str):
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
        include_documents (Union[Unset, bool]): Set this to True if you want to have the response include referenced
            documents along with the spans Default: False.
        maximum_documents_per_span (Union[Unset, int]): The maximum number of documents to retrieve for each span;
            should be no larger than maximum_frequency Default: 10.
        maximum_document_display_length (Union[Unset, int]): The maximum length in tokens of the returned document text
            Default: 100.
        maximum_document_context_length_retrieved (Union[Unset, int]): The maximum number of tokens of the context (on
            each side) to retrieve from the document Default: 250.
        maximum_document_context_length_displayed (Union[Unset, int]): The maximum number of tokens of the context (on
            each side) to display from the document Default: 50.
        filter_method (Union[Unset, Any]): Filtering method for post-processing the retrieved documents, options are
            'none', 'bm25' Default: 'none'.
        filter_bm_25_fields_considered (Union[Unset, Any]): The fields to consider for BM25 filtering, options are
            'prompt', 'response', 'prompt|response' (concat), 'prompt+response' (sum of scores) Default: 'response'.
        filter_bm_25_ratio_to_keep (Union[Unset, float]): The ratio of documents to keep after filtering with BM25
            Default: 1.0.
        include_input_as_tokens (Union[Unset, bool]): Set this to True if you want the response to include the input
            string as a list of string tokens Default: False.
    """

    prompt: str
    response: str
    delimiters: Union[Unset, list[str]] = UNSET
    allow_spans_with_partial_words: Union[Unset, bool] = False
    minimum_span_length: Union[Unset, int] = 1
    maximum_frequency: Union[Unset, int] = 10
    maximum_span_density: Union[Unset, float] = 0.05
    span_ranking_method: Union[Unset, Any] = "length"
    include_documents: Union[Unset, bool] = False
    maximum_documents_per_span: Union[Unset, int] = 10
    maximum_document_display_length: Union[Unset, int] = 100
    maximum_document_context_length_retrieved: Union[Unset, int] = 250
    maximum_document_context_length_displayed: Union[Unset, int] = 50
    filter_method: Union[Unset, Any] = "none"
    filter_bm_25_fields_considered: Union[Unset, Any] = "response"
    filter_bm_25_ratio_to_keep: Union[Unset, float] = 1.0
    include_input_as_tokens: Union[Unset, bool] = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        prompt = self.prompt

        response = self.response

        delimiters: Union[Unset, list[str]] = UNSET
        if not isinstance(self.delimiters, Unset):
            delimiters = self.delimiters

        allow_spans_with_partial_words = self.allow_spans_with_partial_words

        minimum_span_length = self.minimum_span_length

        maximum_frequency = self.maximum_frequency

        maximum_span_density = self.maximum_span_density

        span_ranking_method = self.span_ranking_method

        include_documents = self.include_documents

        maximum_documents_per_span = self.maximum_documents_per_span

        maximum_document_display_length = self.maximum_document_display_length

        maximum_document_context_length_retrieved = self.maximum_document_context_length_retrieved

        maximum_document_context_length_displayed = self.maximum_document_context_length_displayed

        filter_method = self.filter_method

        filter_bm_25_fields_considered = self.filter_bm_25_fields_considered

        filter_bm_25_ratio_to_keep = self.filter_bm_25_ratio_to_keep

        include_input_as_tokens = self.include_input_as_tokens

        field_dict: dict[str, Any] = {}
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
        if maximum_documents_per_span is not UNSET:
            field_dict["maximumDocumentsPerSpan"] = maximum_documents_per_span
        if maximum_document_display_length is not UNSET:
            field_dict["maximumDocumentDisplayLength"] = maximum_document_display_length
        if maximum_document_context_length_retrieved is not UNSET:
            field_dict["maximumDocumentContextLengthRetrieved"] = maximum_document_context_length_retrieved
        if maximum_document_context_length_displayed is not UNSET:
            field_dict["maximumDocumentContextLengthDisplayed"] = maximum_document_context_length_displayed
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
    def from_dict(cls: type[T], src_dict: dict[str, Any]) -> T:
        d = src_dict.copy()
        prompt = d.pop("prompt")

        response = d.pop("response")

        delimiters = cast(list[str], d.pop("delimiters", UNSET))

        allow_spans_with_partial_words = d.pop("allowSpansWithPartialWords", UNSET)

        minimum_span_length = d.pop("minimumSpanLength", UNSET)

        maximum_frequency = d.pop("maximumFrequency", UNSET)

        maximum_span_density = d.pop("maximumSpanDensity", UNSET)

        span_ranking_method = d.pop("spanRankingMethod", UNSET)

        include_documents = d.pop("includeDocuments", UNSET)

        maximum_documents_per_span = d.pop("maximumDocumentsPerSpan", UNSET)

        maximum_document_display_length = d.pop("maximumDocumentDisplayLength", UNSET)

        maximum_document_context_length_retrieved = d.pop("maximumDocumentContextLengthRetrieved", UNSET)

        maximum_document_context_length_displayed = d.pop("maximumDocumentContextLengthDisplayed", UNSET)

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
            maximum_documents_per_span=maximum_documents_per_span,
            maximum_document_display_length=maximum_document_display_length,
            maximum_document_context_length_retrieved=maximum_document_context_length_retrieved,
            maximum_document_context_length_displayed=maximum_document_context_length_displayed,
            filter_method=filter_method,
            filter_bm_25_fields_considered=filter_bm_25_fields_considered,
            filter_bm_25_ratio_to_keep=filter_bm_25_ratio_to_keep,
            include_input_as_tokens=include_input_as_tokens,
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
