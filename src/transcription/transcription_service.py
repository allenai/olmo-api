from flask import current_app
from flask_pydantic_api.utils import UploadedFile

from src.api_interface import APIInterface


class GetTranscriptionRequest(APIInterface):
    audio: UploadedFile


class GetTranscriptionResponse(APIInterface):
    text: str


def get_transcription(request: GetTranscriptionRequest):
    current_app.logger.info("get_transcription")

    return GetTranscriptionResponse(text="Response")
