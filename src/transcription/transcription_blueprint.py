from flask import Blueprint
from flask_pydantic_api.api_wrapper import pydantic_api

from src.transcription.transcription_service import GetTranscriptionRequest, GetTranscriptionResponse, get_transcription


def create_transcription_blueprint() -> Blueprint:
    transcription_blueprint = Blueprint("transcription", __name__)

    @transcription_blueprint.post("/")
    @pydantic_api(name="Transcribe audio", tags=["v4", "transcribe"])
    def transcribe(request: GetTranscriptionRequest) -> GetTranscriptionResponse:
        return get_transcription(request)

    return transcription_blueprint
