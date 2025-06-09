from src.api_interface import APIInterface

from pydantic import Field

from flask_pydantic_api.utils import UploadedFile

from flask import jsonify, current_app

class GetTranscriptionRequest(APIInterface):
    # audio: UploadedFile = Field(...options....)
    audio: UploadedFile | None = Field(default=None) # can we enforce this as required

class GetTranscriptionResponse(APIInterface):
    text: str | None

def get_transcription(request: GetTranscriptionRequest):

    # audio = request.audio
    current_app.logger.info("get_transcription")

    return GetTranscriptionResponse(text="Response")
