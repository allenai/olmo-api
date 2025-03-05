import logging

from werkzeug import exceptions

from src.config.get_config import cfg
from src.config.Model import Model


def get_models_by_host(host: str) -> list[Model]:
    return [model for model in cfg.models if model.host == host]


def get_model_by_host_and_id(host: str, id: str) -> Model:
    model = next((model for model in cfg.models if model.host == host and model.id == id), None)

    if model is None:
        logging.getLogger().error(
            "Couldn't find model/host combination %(model)s/%(host)s", extra={"model": id, "host": host}
        )

        error_message = f"Invalid model/host combination {id}/{host}"
        raise exceptions.BadRequest(error_message)

    return model
