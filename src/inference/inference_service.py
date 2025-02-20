from typing import Sequence, cast

from src import config
from src.config.Model import Model, MultiModalModel


def get_available_models() -> Sequence[Model | MultiModalModel]:
    all_models = []

    for host in config.model_hosts:
        host_config = cast(config.BaseInferenceEngineConfig, getattr(config.cfg, host))
        default_model = host_config.default_model
        models_for_host: list[Model | MultiModalModel] = []

        for model in host_config.available_models:
            # Add the default model first, and other models afterward
            if model.id == default_model:
                models_for_host.insert(0, model)
            else:
                models_for_host.append(model)

        # Now add all models for the current host (with the default first) to the main list
        all_models.extend(models_for_host)
    return all_models
