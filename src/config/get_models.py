from src.config.get_config import cfg
from src.config.Model import Model


def get_models_by_host(host: str) -> list[Model]:
    return [model for model in cfg.models if model.host == host]


def get_model_by_host_and_id(host: str, id: str) -> Model:
    return next(model for model in cfg.models if model.host == host and model.id == id)
