from src.config.Config import Model
from src.config.get_config import cfg
from src.config.ModelConfig import ModelHost


def get_models_by_host(host: ModelHost) -> list[Model]:
    return list(filter(lambda model: model.host is host, cfg.models))
