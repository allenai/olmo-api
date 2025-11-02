import structlog

from sqlalchemy.orm import Session
from werkzeug import exceptions

from src.dao.engine_models.model_config import ModelConfig, MultiModalModelConfig
from src.model_config.get_model_config_service import get_single_model_config_admin

logger = structlog.get_logger(__name__)


def get_model_by_host_and_id(session: Session, host: str, id: str) -> ModelConfig | MultiModalModelConfig:
    model = get_single_model_config_admin(session, id)

    if model is None or model.host != host:
        logger.error("model_host_combination_not_found", model_id=id, host=host)

        invalid_model_and_host_message = f"Invalid model/host combination {id}/{host}"
        raise exceptions.BadRequest(invalid_model_and_host_message)

    return model
