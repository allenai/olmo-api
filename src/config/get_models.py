import logging

from werkzeug import exceptions

from pydantic_ai.models import Model
from src.dao.engine_models.model_config import ModelConfig, MultiModalModelConfig
from src.dao.flask_sqlalchemy_session import current_session
from src.model_config.get_model_config_service import get_single_model_config_admin
from src.pydantic_inference.pydantic_model_service import get_pydantic_model


def get_model_by_id(id: str) -> ModelConfig | MultiModalModelConfig:
    model = get_single_model_config_admin(current_session, model_id=id)

    if model is None:
        logging.getLogger().error("Couldn't find model %s", id)

        invalid_model_message = f"Invalid model {id}"
        raise exceptions.BadRequest(invalid_model_message)

    return model


def get_pydantic_model_by_id(id: str) -> Model:
    model_config = get_model_by_id(id)
    return get_pydantic_model(model_config)
