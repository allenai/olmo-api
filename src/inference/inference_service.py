import dataclasses

from src import config
from typing import Sequence


@dataclasses.dataclass
class ModelEntity:
    id: str
    host: str
    name: str
    description: str
    model_type: str


def get_available_models() -> Sequence[ModelEntity]:
    all_models = []
    for host in config.model_hosts:
        for model in getattr(config.cfg, host).available_models:
            all_models.append(
                ModelEntity(
                    id=model.id,
                    host=host,
                    name=model.name,
                    description=model.description,
                    model_type=model.model_type,
                )
            )

    return all_models
