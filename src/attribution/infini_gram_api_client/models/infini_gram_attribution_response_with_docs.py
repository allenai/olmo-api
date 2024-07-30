from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.attribution_span_with_documents import AttributionSpanWithDocuments


T = TypeVar("T", bound="InfiniGramAttributionResponseWithDocs")


@_attrs_define
class InfiniGramAttributionResponseWithDocs:
    """
    Attributes:
        index (str):
        spans (List['AttributionSpanWithDocuments']):
    """

    index: str
    spans: List["AttributionSpanWithDocuments"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        index = self.index

        spans = []
        for spans_item_data in self.spans:
            spans_item = spans_item_data.to_dict()
            spans.append(spans_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "index": index,
                "spans": spans,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.attribution_span_with_documents import AttributionSpanWithDocuments

        d = src_dict.copy()
        index = d.pop("index")

        spans = []
        _spans = d.pop("spans")
        for spans_item_data in _spans:
            spans_item = AttributionSpanWithDocuments.from_dict(spans_item_data)

            spans.append(spans_item)

        infini_gram_attribution_response_with_docs = cls(
            index=index,
            spans=spans,
        )

        infini_gram_attribution_response_with_docs.additional_properties = d
        return infini_gram_attribution_response_with_docs

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
