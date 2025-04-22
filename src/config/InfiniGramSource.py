from typing import Self, Union

from pydantic import BaseModel, ModelWrapValidatorHandler, model_validator


class InfiniGramSource(BaseModel):
    name: str
    usage: str
    display_name: Union[str, None]
    url: Union[str, None]
    secondary_name: Union[str, None]

    @model_validator(mode="wrap")
    @classmethod
    def generate_initial_values(cls, data: dict, handler: ModelWrapValidatorHandler[Self]):
        initial_values = {
            "name": data.get("name"),
            "usage": data.get("usage"),
            "display_name": data.get("display_name") or data.get("name"),
            "url": data.get("url") or f"https://huggingface.co/datasets/allenai/{data.get('name')}",
            "secondary_name": data.get("secondary_name"),
        }

        validated_values = handler(initial_values)

        return validated_values


def map_infinigram_sources(infinigram_sources: list[dict]) -> dict[str, InfiniGramSource]:
    source_dict = {}
    for item in infinigram_sources or []:
        validated_source = InfiniGramSource.model_validate(item)
        source_dict[validated_source.name] = validated_source

    return source_dict
