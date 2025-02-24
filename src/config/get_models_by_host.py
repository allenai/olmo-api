from src.config import Model, cfg
from src.config.ModelConfig import ModelHost


def get_models_by_host(host: ModelHost) -> list[Model]:
    return list(filter(lambda model: model.host is host, cfg.models))
