from flask import Blueprint, Response, jsonify
from flask_pydantic_api.api_wrapper import pydantic_api
from sqlalchemy import select
from sqlalchemy.orm import Session, selectin_polymorphic, sessionmaker

from src.config.ModelConfig import FileRequiredToPromptOption, ModelHost, ModelType
from src.dao.engine_models.model_config import ModelConfig, MultiModalModelConfig, PromptType


def create_model_config_blueprint(session_maker: sessionmaker[Session]) -> Blueprint:
    model_config_blueprint = Blueprint(name="model_config", import_name=__name__)

    @model_config_blueprint.get("/")
    @pydantic_api(name="Get available models and their configuration", tags=["v4", "models", "model configuration"])
    def get_model_configs() -> Response:
        with session_maker.begin() as session:
            polymorphic_loader_opt = selectin_polymorphic(ModelConfig, [ModelConfig, MultiModalModelConfig])
            stmt = select(ModelConfig).options(polymorphic_loader_opt)
            rows = session.scalars(stmt).all()

            return jsonify(rows)

    @model_config_blueprint.post("/")
    def make_model_configs():
        with session_maker.begin() as session:
            session.add(
                ModelConfig(
                    id="olmo-2-0325-32b-instruct",
                    host=ModelHost.Modal,
                    name="OLMo 2 32B Instruct",
                    order=0,
                    description="Ai2's 32B model using the OLMo2 architecture.",
                    model_type=ModelType.Chat,
                    model_id_on_host="OLMo-2-0325-32B-Instruct-COMBO",
                    prompt_type=PromptType.TEXT_ONLY,
                    internal=False,
                    family_id="olmo",
                    family_name="OLMo",
                )
            )

            session.add(
                MultiModalModelConfig(
                    id="mm-olmo-uber-model-v4-synthetic",
                    host=ModelHost.Modal,
                    name="Molmo",
                    order=1,
                    description="Molmo",
                    model_type=ModelType.Chat,
                    model_id_on_host="OLMo-2-0325-32B-Instruct-COMBO",
                    prompt_type=PromptType.MULTI_MODAL,
                    internal=False,
                    accepted_file_types=["image/*"],
                    max_files_per_message=1,
                    require_file_to_prompt=FileRequiredToPromptOption.FirstMessage,
                    allow_files_in_followups=False,
                )
            )

            return ("", 204)

    return model_config_blueprint
