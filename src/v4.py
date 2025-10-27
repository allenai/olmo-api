from flask import Blueprint
from sqlalchemy.orm import Session, sessionmaker

from src import db
from src.admin.admin_blueprint import create_admin_blueprint
from src.agent.agent_blueprint import create_agents_blueprint
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.model_config.model_config_blueprint import create_model_config_blueprint
from src.prompt_template.prompt_template_blueprint import create_prompt_template_blueprint
from src.thread.threads_blueprint import create_threads_blueprint
from src.transcription.transcription_blueprint import create_transcription_blueprint


def create_v4_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage, session_maker: sessionmaker[Session]):
    v4_blueprint = Blueprint(name="v4", import_name=__name__)

    v4_blueprint.register_blueprint(create_model_config_blueprint(session_maker), url_prefix="/models", name="models")
    v4_blueprint.register_blueprint(
        create_admin_blueprint(session_maker),
        url_prefix="/admin/models",
        name="admin/models",
    )

    v4_blueprint.register_blueprint(
        blueprint=create_threads_blueprint(dbc=dbc, storage_client=storage_client),
        url_prefix="/threads",
        name="threads",
    )

    v4_blueprint.register_blueprint(
        blueprint=create_transcription_blueprint(), url_prefix="/transcribe", name="transcribe"
    )

    v4_blueprint.register_blueprint(
        create_prompt_template_blueprint(), url_prefix="/prompt-templates", name="prompt-template"
    )

    v4_blueprint.register_blueprint(
        create_agents_blueprint(dbc=dbc, storage_client=storage_client), url_prefix="/agents", name="agent"
    )

    return v4_blueprint
