import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker
from werkzeug import exceptions

from src.config.get_config import get_config
from src.config.Model import MultiModalModel
from src.dao.engine_models.model_config import ModelConfig, MultiModalModelConfig, PromptType
from src.model_config.get_model_config_service import get_single_model_config_admin


def get_model_by_host_and_id(
    host: str, id: str, session_maker: sessionmaker[Session]
) -> ModelConfig | MultiModalModelConfig:
    cfg = get_config()
    if cfg.feature_flags.enable_dynamic_model_config:
        model = get_single_model_config_admin(session_maker, id)
    else:
        model_from_config = next((model for model in cfg.models if model.host == host and model.id == id), None)

        if model_from_config is None:
            model = None
        else:
            model = ModelConfig(
                id=model_from_config.id,
                host=model_from_config.host,
                name=model_from_config.name,
                description=model_from_config.description,
                model_type=model_from_config.model_type,
                model_id_on_host=model_from_config.compute_source_id,
                internal=False,
                prompt_type=PromptType.TEXT_ONLY,
                default_system_prompt=model_from_config.system_prompt,
                family_id=model_from_config.family_id,
                family_name=model_from_config.family_name,
                available_time=model_from_config.available_time,
                deprecation_time=model_from_config.deprecation_time,
            )

            if isinstance(model_from_config, MultiModalModel):
                model = MultiModalModelConfig(
                    id=model_from_config.id,
                    host=model_from_config.host,
                    name=model_from_config.name,
                    description=model_from_config.description,
                    model_type=model_from_config.model_type,
                    model_id_on_host=model_from_config.compute_source_id,
                    internal=False,
                    prompt_type=PromptType.MULTI_MODAL,
                    default_system_prompt=model_from_config.system_prompt,
                    family_id=model_from_config.family_id,
                    family_name=model_from_config.family_name,
                    available_time=model_from_config.available_time,
                    deprecation_time=model_from_config.deprecation_time,
                    accepted_file_types=model_from_config.accepted_file_types,
                    max_files_per_message=model_from_config.max_files_per_message,
                    require_file_to_prompt=model_from_config.require_file_to_prompt,
                    max_total_file_size=model_from_config.max_total_file_size,
                    allow_files_in_followups=model_from_config.allow_files_in_followups,
                )

            # HACK: This gets around the Pydantic validations we do to validate files
            model.order = 0
            model.created_time = datetime.now(UTC)
            model.updated_time = datetime.now(UTC)

    if model is None or model.host != host:
        logging.getLogger().error("Couldn't find model/host combination %s/%s", id, host)

        error_message = f"Invalid model/host combination {id}/{host}"
        raise exceptions.BadRequest(error_message)

    return model
