from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.infini_gram_document_response_metadata import InfiniGramDocumentResponseMetadata


T = TypeVar("T", bound="InfiniGramDocumentResponse")


@_attrs_define
class InfiniGramDocumentResponse:
    """
    Attributes:
        index (str):
        document_index (int):
        document_length (int):
        display_length (int):
        metadata (InfiniGramDocumentResponseMetadata):
        token_ids (List[int]):
        text (str):
    """

    index: str
    document_index: int
    document_length: int
    display_length: int
    metadata: "InfiniGramDocumentResponseMetadata"
    token_ids: List[int]
    text: str
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        index = self.index

        document_index = self.document_index

        document_length = self.document_length

        display_length = self.display_length

        metadata = self.metadata.to_dict()

        token_ids = self.token_ids

        text = self.text

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "index": index,
                "documentIndex": document_index,
                "documentLength": document_length,
                "displayLength": display_length,
                "metadata": metadata,
                "tokenIds": token_ids,
                "text": text,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.infini_gram_document_response_metadata import InfiniGramDocumentResponseMetadata

        d = src_dict.copy()
        index = d.pop("index")

        document_index = d.pop("documentIndex")

        document_length = d.pop("documentLength")

        display_length = d.pop("displayLength")

        metadata = InfiniGramDocumentResponseMetadata.from_dict(d.pop("metadata"))

        token_ids = cast(List[int], d.pop("tokenIds"))

        text = d.pop("text")

        infini_gram_document_response = cls(
            index=index,
            document_index=document_index,
            document_length=document_length,
            display_length=display_length,
            metadata=metadata,
            token_ids=token_ids,
            text=text,
        )

        infini_gram_document_response.additional_properties = d
        return infini_gram_document_response

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
