from dataclasses import dataclass
from typing import Optional, Sequence

from src import config


@dataclass
class ModelEntity:
    id: str
    host: str
    name: str
    description: str
    model_type: str
    is_deprecated: bool
    is_visible: bool
    family_id: Optional[str] = None
    family_name: Optional[str] = None


def get_available_models() -> Sequence[ModelEntity]:
    all_models = []

    for host in config.model_hosts:
        host_config = getattr(config.cfg, host)
        default_model = host_config.default_model
        models_for_host: list[ModelEntity] = []

        for model in host_config.available_models:
            model_entity = model.model_dump()

            # Add the default model first, and other models afterward
            if model.id == default_model:
                models_for_host.insert(0, model_entity)
            else:
                models_for_host.append(model_entity)

        # Now add all models for the current host (with the default first) to the main list
        all_models.extend(models_for_host)
    return all_models
