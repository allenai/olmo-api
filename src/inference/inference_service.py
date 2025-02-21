from typing import Sequence

from src import config
from src.config.Model import Model, MultiModalModel


def get_available_models() -> Sequence[Model | MultiModalModel]:
    return config.cfg.models
