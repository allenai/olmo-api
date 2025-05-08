import logging

from sqlalchemy.orm import Session, sessionmaker
from werkzeug import exceptions

from src.config.get_config import cfg
from src.config.Model import Model
from src.dao.engine_models.model_config import ModelConfig
from src.model_config.get_model_config_service import get_single_model_config_admin


def get_models_by_host(host: str) -> list[Model]:
    return [model for model in cfg.models if model.host == host]


def get_model_by_host_and_id(host: str, id: str, session_maker: sessionmaker[Session]) -> ModelConfig:
    model = get_single_model_config_admin(session_maker, id)

    if model is None or model.host != host:
        logging.getLogger().error("Couldn't find model/host combination %s/%s", id, host)

        error_message = f"Invalid model/host combination {id}/{host}"
        raise exceptions.BadRequest(error_message)

    return model
