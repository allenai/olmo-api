from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

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
        needle_offset (int):
        metadata (InfiniGramDocumentResponseMetadata):
        token_ids (list[int]):
        text (str):
        relevance_score (Union[None, Unset, float]):
        display_length_long (Union[None, Unset, int]):
        needle_offset_long (Union[None, Unset, int]):
        text_long (Union[None, Unset, str]):
    """

    index: str
    document_index: int
    document_length: int
    display_length: int
    needle_offset: int
    metadata: "InfiniGramDocumentResponseMetadata"
    token_ids: list[int]
    text: str
    relevance_score: Union[None, Unset, float] = UNSET
    display_length_long: Union[None, Unset, int] = UNSET
    needle_offset_long: Union[None, Unset, int] = UNSET
    text_long: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        index = self.index

        document_index = self.document_index

        document_length = self.document_length

        display_length = self.display_length

        needle_offset = self.needle_offset

        metadata = self.metadata.to_dict()

        token_ids = self.token_ids

        text = self.text

        relevance_score: Union[None, Unset, float]
        if isinstance(self.relevance_score, Unset):
            relevance_score = UNSET
        else:
            relevance_score = self.relevance_score

        display_length_long: Union[None, Unset, int]
        if isinstance(self.display_length_long, Unset):
            display_length_long = UNSET
        else:
            display_length_long = self.display_length_long

        needle_offset_long: Union[None, Unset, int]
        if isinstance(self.needle_offset_long, Unset):
            needle_offset_long = UNSET
        else:
            needle_offset_long = self.needle_offset_long

        text_long: Union[None, Unset, str]
        if isinstance(self.text_long, Unset):
            text_long = UNSET
        else:
            text_long = self.text_long

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "index": index,
                "documentIndex": document_index,
                "documentLength": document_length,
                "displayLength": display_length,
                "needleOffset": needle_offset,
                "metadata": metadata,
                "tokenIds": token_ids,
                "text": text,
            }
        )
        if relevance_score is not UNSET:
            field_dict["relevanceScore"] = relevance_score
        if display_length_long is not UNSET:
            field_dict["displayLengthLong"] = display_length_long
        if needle_offset_long is not UNSET:
            field_dict["needleOffsetLong"] = needle_offset_long
        if text_long is not UNSET:
            field_dict["textLong"] = text_long

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: dict[str, Any]) -> T:
        from ..models.infini_gram_document_response_metadata import InfiniGramDocumentResponseMetadata

        d = src_dict.copy()
        index = d.pop("index")

        document_index = d.pop("documentIndex")

        document_length = d.pop("documentLength")

        display_length = d.pop("displayLength")

        needle_offset = d.pop("needleOffset")

        metadata = InfiniGramDocumentResponseMetadata.from_dict(d.pop("metadata"))

        token_ids = cast(list[int], d.pop("tokenIds"))

        text = d.pop("text")

        def _parse_relevance_score(data: object) -> Union[None, Unset, float]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, float], data)

        relevance_score = _parse_relevance_score(d.pop("relevanceScore", UNSET))

        def _parse_display_length_long(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        display_length_long = _parse_display_length_long(d.pop("displayLengthLong", UNSET))

        def _parse_needle_offset_long(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        needle_offset_long = _parse_needle_offset_long(d.pop("needleOffsetLong", UNSET))

        def _parse_text_long(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        text_long = _parse_text_long(d.pop("textLong", UNSET))

        infini_gram_document_response = cls(
            index=index,
            document_index=document_index,
            document_length=document_length,
            display_length=display_length,
            needle_offset=needle_offset,
            metadata=metadata,
            token_ids=token_ids,
            text=text,
            relevance_score=relevance_score,
            display_length_long=display_length_long,
            needle_offset_long=needle_offset_long,
            text_long=text_long,
        )

        infini_gram_document_response.additional_properties = d
        return infini_gram_document_response

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
