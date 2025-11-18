from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.validation_error import ValidationError


T = TypeVar("T", bound="RequestValidationError")


@_attrs_define
class RequestValidationError:
    """
    Attributes:
        title (str):
        type_ (str):
        status (int):
        errors (list['ValidationError']):
    """

    title: str
    type_: str
    status: int
    errors: list["ValidationError"]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        type_ = self.type_

        status = self.status

        errors = []
        for errors_item_data in self.errors:
            errors_item = errors_item_data.to_dict()
            errors.append(errors_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "title": title,
                "type": type_,
                "status": status,
                "errors": errors,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: dict[str, Any]) -> T:
        from ..models.validation_error import ValidationError

        d = src_dict.copy()
        title = d.pop("title")

        type_ = d.pop("type")

        status = d.pop("status")

        errors = []
        _errors = d.pop("errors")
        for errors_item_data in _errors:
            errors_item = ValidationError.from_dict(errors_item_data)

            errors.append(errors_item)

        request_validation_error = cls(
            title=title,
            type_=type_,
            status=status,
            errors=errors,
        )

        request_validation_error.additional_properties = d
        return request_validation_error

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
