from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.attribution_span import AttributionSpan


T = TypeVar("T", bound="InfiniGramAttributionResponse")


@_attrs_define
class InfiniGramAttributionResponse:
    """
    Attributes:
        index (str):
        spans (List['AttributionSpan']):
        input_tokens (Union[List[str], None]):
    """

    index: str
    spans: List["AttributionSpan"]
    input_tokens: Union[List[str], None]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        index = self.index

        spans = []
        for spans_item_data in self.spans:
            spans_item = spans_item_data.to_dict()
            spans.append(spans_item)

        input_tokens: Union[List[str], None]
        if isinstance(self.input_tokens, list):
            input_tokens = self.input_tokens

        else:
            input_tokens = self.input_tokens

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "index": index,
                "spans": spans,
                "inputTokens": input_tokens,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.attribution_span import AttributionSpan

        d = src_dict.copy()
        index = d.pop("index")

        spans = []
        _spans = d.pop("spans")
        for spans_item_data in _spans:
            spans_item = AttributionSpan.from_dict(spans_item_data)

            spans.append(spans_item)

        def _parse_input_tokens(data: object) -> Union[List[str], None]:
            if data is None:
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                input_tokens_type_0 = cast(List[str], data)

                return input_tokens_type_0
            except:  # noqa: E722
                pass
            return cast(Union[List[str], None], data)

        input_tokens = _parse_input_tokens(d.pop("inputTokens"))

        infini_gram_attribution_response = cls(
            index=index,
            spans=spans,
            input_tokens=input_tokens,
        )

        infini_gram_attribution_response.additional_properties = d
        return infini_gram_attribution_response

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
