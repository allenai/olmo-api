from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.document_with_pointer import DocumentWithPointer


T = TypeVar("T", bound="AttributionSpanWithDocuments")


@_attrs_define
class AttributionSpanWithDocuments:
    """
    Attributes:
        left (int):
        right (int):
        length (int):
        text (str):
        token_ids (List[int]):
        documents (List['DocumentWithPointer']):
    """

    left: int
    right: int
    length: int
    text: str
    token_ids: List[int]
    documents: List["DocumentWithPointer"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        left = self.left

        right = self.right

        length = self.length

        text = self.text

        token_ids = self.token_ids

        documents = []
        for documents_item_data in self.documents:
            documents_item = documents_item_data.to_dict()
            documents.append(documents_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "left": left,
                "right": right,
                "length": length,
                "text": text,
                "tokenIds": token_ids,
                "documents": documents,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.document_with_pointer import DocumentWithPointer

        d = src_dict.copy()
        left = d.pop("left")

        right = d.pop("right")

        length = d.pop("length")

        text = d.pop("text")

        token_ids = cast(List[int], d.pop("tokenIds"))

        documents = []
        _documents = d.pop("documents")
        for documents_item_data in _documents:
            documents_item = DocumentWithPointer.from_dict(documents_item_data)

            documents.append(documents_item)

        attribution_span_with_documents = cls(
            left=left,
            right=right,
            length=length,
            text=text,
            token_ids=token_ids,
            documents=documents,
        )

        attribution_span_with_documents.additional_properties = d
        return attribution_span_with_documents

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
