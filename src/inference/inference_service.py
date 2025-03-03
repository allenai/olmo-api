from collections.abc import Sequence

from src.config import get_config
from src.config.Model import Model, MultiModalModel


def get_available_models() -> Sequence[Model | MultiModalModel]:
    return get_config.cfg.models
