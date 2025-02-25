from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.document import Document


T = TypeVar("T", bound="SearchResponse")


@_attrs_define
class SearchResponse:
    """
    Attributes:
        index (str):
        documents (List['Document']):
        page (int):
        page_size (int):
        page_count (int):
        total_documents (int):
    """

    index: str
    documents: List["Document"]
    page: int
    page_size: int
    page_count: int
    total_documents: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        index = self.index

        documents = []
        for documents_item_data in self.documents:
            documents_item = documents_item_data.to_dict()
            documents.append(documents_item)

        page = self.page

        page_size = self.page_size

        page_count = self.page_count

        total_documents = self.total_documents

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "index": index,
                "documents": documents,
                "page": page,
                "pageSize": page_size,
                "pageCount": page_count,
                "totalDocuments": total_documents,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.document import Document

        d = src_dict.copy()
        index = d.pop("index")

        documents = []
        _documents = d.pop("documents")
        for documents_item_data in _documents:
            documents_item = Document.from_dict(documents_item_data)

            documents.append(documents_item)

        page = d.pop("page")

        page_size = d.pop("pageSize")

        page_count = d.pop("pageCount")

        total_documents = d.pop("totalDocuments")

        search_response = cls(
            index=index,
            documents=documents,
            page=page,
            page_size=page_size,
            page_count=page_count,
            total_documents=total_documents,
        )

        search_response.additional_properties = d
        return search_response

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
