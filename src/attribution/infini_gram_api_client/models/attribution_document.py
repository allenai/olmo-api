from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.attribution_document_metadata import AttributionDocumentMetadata


T = TypeVar("T", bound="AttributionDocument")


@_attrs_define
class AttributionDocument:
    """
    Attributes:
        document_index (int):
        document_length (int):
        display_length (int):
        needle_offset (int):
        metadata (AttributionDocumentMetadata):
        token_ids (list[int]):
        text (str):
        display_length_long (int):
        needle_offset_long (int):
        text_long (str):
        display_offset_snippet (int):
        needle_offset_snippet (int):
        text_snippet (str):
        blocked (Union[Unset, bool]):  Default: False.
    """

    document_index: int
    document_length: int
    display_length: int
    needle_offset: int
    metadata: "AttributionDocumentMetadata"
    token_ids: list[int]
    text: str
    display_length_long: int
    needle_offset_long: int
    text_long: str
    display_offset_snippet: int
    needle_offset_snippet: int
    text_snippet: str
    blocked: Union[Unset, bool] = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        document_index = self.document_index

        document_length = self.document_length

        display_length = self.display_length

        needle_offset = self.needle_offset

        metadata = self.metadata.to_dict()

        token_ids = self.token_ids

        text = self.text

        display_length_long = self.display_length_long

        needle_offset_long = self.needle_offset_long

        text_long = self.text_long

        display_offset_snippet = self.display_offset_snippet

        needle_offset_snippet = self.needle_offset_snippet

        text_snippet = self.text_snippet

        blocked = self.blocked

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "documentIndex": document_index,
            "documentLength": document_length,
            "displayLength": display_length,
            "needleOffset": needle_offset,
            "metadata": metadata,
            "tokenIds": token_ids,
            "text": text,
            "displayLengthLong": display_length_long,
            "needleOffsetLong": needle_offset_long,
            "textLong": text_long,
            "displayOffsetSnippet": display_offset_snippet,
            "needleOffsetSnippet": needle_offset_snippet,
            "textSnippet": text_snippet,
        })
        if blocked is not UNSET:
            field_dict["blocked"] = blocked

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: dict[str, Any]) -> T:
        from ..models.attribution_document_metadata import AttributionDocumentMetadata

        d = src_dict.copy()
        document_index = d.pop("documentIndex")

        document_length = d.pop("documentLength")

        display_length = d.pop("displayLength")

        needle_offset = d.pop("needleOffset")

        metadata = AttributionDocumentMetadata.from_dict(d.pop("metadata"))

        token_ids = cast(list[int], d.pop("tokenIds"))

        text = d.pop("text")

        display_length_long = d.pop("displayLengthLong")

        needle_offset_long = d.pop("needleOffsetLong")

        text_long = d.pop("textLong")

        display_offset_snippet = d.pop("displayOffsetSnippet")

        needle_offset_snippet = d.pop("needleOffsetSnippet")

        text_snippet = d.pop("textSnippet")

        blocked = d.pop("blocked", UNSET)

        attribution_document = cls(
            document_index=document_index,
            document_length=document_length,
            display_length=display_length,
            needle_offset=needle_offset,
            metadata=metadata,
            token_ids=token_ids,
            text=text,
            display_length_long=display_length_long,
            needle_offset_long=needle_offset_long,
            text_long=text_long,
            display_offset_snippet=display_offset_snippet,
            needle_offset_snippet=needle_offset_snippet,
            text_snippet=text_snippet,
            blocked=blocked,
        )

        attribution_document.additional_properties = d
        return attribution_document

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
