from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="Problem")


@_attrs_define
class Problem:
    """
    Example:
        {'title': 'Request validation error.', 'errors': [], 'type': 'request-validation-failed', 'status': 422}

    Attributes:
        title (str):
        type_ (str):
        status (int):
        detail (Union[None, str]):
    """

    title: str
    type_: str
    status: int
    detail: Union[None, str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        type_ = self.type_

        status = self.status

        detail: Union[None, str]
        detail = self.detail

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "title": title,
            "type": type_,
            "status": status,
            "detail": detail,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: dict[str, Any]) -> T:
        d = src_dict.copy()
        title = d.pop("title")

        type_ = d.pop("type")

        status = d.pop("status")

        def _parse_detail(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        detail = _parse_detail(d.pop("detail"))

        problem = cls(
            title=title,
            type_=type_,
            status=status,
            detail=detail,
        )

        problem.additional_properties = d
        return problem

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
