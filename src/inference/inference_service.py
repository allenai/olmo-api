from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence, cast

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

        for model in cast(Sequence[config.Model], host_config.available_models):
            now = datetime.now()

            model_is_available = now >= model.available_time
            model_is_before_deprecation_time = (
                now < model.deprecation_time
                if model.deprecation_time is not None
                else True
            )

            model_entity = ModelEntity(
                id=model.id,
                host=host,
                name=model.name,
                description=model.description,
                model_type=model.model_type,
                is_deprecated=not model_is_available
                or not model_is_before_deprecation_time,
                is_visible=model_is_available and model_is_before_deprecation_time,
                family_id=model.family_id,
                family_name=model.family_name,
            )

            # Add the default model first, and other models afterward
            if model.id == default_model:
                models_for_host.insert(0, model_entity)
            else:
                models_for_host.append(model_entity)

        # Now add all models for the current host (with the default first) to the main list
        all_models.extend(models_for_host)
    return all_models
