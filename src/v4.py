from flask import Blueprint, Response, stream_with_context
from sqlalchemy.orm import Session, sessionmaker

from src import db
from src.admin.admin_blueprint import create_admin_blueprint
from src.chat import chat_service, pydantic_chat_service
from src.message.GoogleCloudStorage import GoogleCloudStorage
from src.message.v4_message_blueprint import create_v4_message_blueprint
from src.model_config.model_config_blueprint import create_model_config_blueprint
from src.thread.threads_blueprint import create_threads_blueprint
from src.transcription.transcription_blueprint import create_transcription_blueprint


def create_v4_blueprint(dbc: db.Client, storage_client: GoogleCloudStorage, session_maker: sessionmaker[Session]):
    v4_blueprint = Blueprint(name="v4", import_name=__name__)

    v4_blueprint.register_blueprint(
        blueprint=create_v4_message_blueprint(dbc, storage_client=storage_client, session_maker=session_maker),
        url_prefix="/message",
        name="message",
    )

    v4_blueprint.register_blueprint(create_model_config_blueprint(session_maker), url_prefix="/models", name="models")
    v4_blueprint.register_blueprint(
        create_admin_blueprint(session_maker),
        url_prefix="/admin/models",
        name="admin/models",
    )

    v4_blueprint.register_blueprint(
        blueprint=create_threads_blueprint(dbc=dbc, storage_client=storage_client, session_maker=session_maker),
        url_prefix="/threads",
        name="threads",
    )

    v4_blueprint.register_blueprint(
        blueprint=create_transcription_blueprint(session_maker), url_prefix="/transcribe", name="transcribe"
    )

    @v4_blueprint.post("/test-message")
    def test_message():
        model = chat_service.get_test_model("OLMo-2-0425-1B-Instruct")
        return Response(
            stream_with_context(
                chat_service.stream_message(model, user_prompt="<thought>thinking about a lot of things</thought>")
            ),
            mimetype="application/jsonl",
        )

    @v4_blueprint.post("/test-pydantic")
    def test_pydantic():
        return Response(stream_with_context(pydantic_chat_service.stream_message("Tell me about lions")))

    return v4_blueprint
