from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="AttributionDocument")


@_attrs_define
class AttributionDocument:
    """
    Attributes:
        shard (int):
        pointer (int):
        document_index (int):
    """

    shard: int
    pointer: int
    document_index: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        shard = self.shard

        pointer = self.pointer

        document_index = self.document_index

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "shard": shard,
                "pointer": pointer,
                "documentIndex": document_index,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        shard = d.pop("shard")

        pointer = d.pop("pointer")

        document_index = d.pop("documentIndex")

        attribution_document = cls(
            shard=shard,
            pointer=pointer,
            document_index=document_index,
        )

        attribution_document.additional_properties = d
        return attribution_document

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
