from flask import Blueprint, Response, jsonify
from flask_pydantic_api.api_wrapper import pydantic_api

from pydantic import ValidationError

from src.config.get_config import cfg
from src.error import handle_validation_error
from src.transcription.transcription_service import (
    GetTranscriptionRequest,
    GetTranscriptionResponse,
    get_transcription
)

def create_transcription_blueprint() -> Blueprint:
    transcription_blueprint = Blueprint("transcription", __name__)

    @transcription_blueprint.post("/")
    @pydantic_api(name="Transcribe audio", tags=["v4", "transcribe"])
    def transcribe(request: GetTranscriptionRequest) -> GetTranscriptionResponse:
        try:
            return get_transcription(request)
        except ValidationError as e:
            return handle_validation_error(e)

    return transcription_blueprint
