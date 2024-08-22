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
    """

    query: str
    delimiters: Union[Unset, List[str]] = UNSET
    minimum_span_length: Union[Unset, int] = 5
    maximum_frequency: Union[Unset, int] = 10
    include_documents: Union[Unset, bool] = False
    maximum_document_display_length: Union[Unset, int] = 100
    include_input_as_tokens: Union[Unset, bool] = False
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        query = self.query

        delimiters: Union[Unset, List[str]] = UNSET
        if not isinstance(self.delimiters, Unset):
            delimiters = self.delimiters

        minimum_span_length = self.minimum_span_length

        maximum_frequency = self.maximum_frequency

        include_documents = self.include_documents

        maximum_document_display_length = self.maximum_document_display_length

        include_input_as_tokens = self.include_input_as_tokens

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if delimiters is not UNSET:
            field_dict["delimiters"] = delimiters
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

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        query = d.pop("query")

        delimiters = cast(List[str], d.pop("delimiters", UNSET))

        minimum_span_length = d.pop("minimumSpanLength", UNSET)

        maximum_frequency = d.pop("maximumFrequency", UNSET)

        include_documents = d.pop("includeDocuments", UNSET)

        maximum_document_display_length = d.pop("maximumDocumentDisplayLength", UNSET)

        include_input_as_tokens = d.pop("includeInputAsTokens", UNSET)

        attribution_request = cls(
            query=query,
            delimiters=delimiters,
            minimum_span_length=minimum_span_length,
            maximum_frequency=maximum_frequency,
            include_documents=include_documents,
            maximum_document_display_length=maximum_document_display_length,
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
