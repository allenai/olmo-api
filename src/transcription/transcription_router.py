"""
Transcription Router (FastAPI) - V4
------------------------------------

FastAPI router for audio transcription operations.
Converted from Flask blueprint in transcription_blueprint.py.
"""

from fastapi import APIRouter, File, UploadFile

from src.dao.fastapi_sqlalchemy_session import DBSession
from src.transcription.transcription_service import GetTranscriptionRequest, GetTranscriptionResponse, get_transcription

router = APIRouter(tags=["v4", "transcribe"])


@router.post("/", response_model=GetTranscriptionResponse)
async def transcribe(session: DBSession, audio: UploadFile = File(...)) -> GetTranscriptionResponse:
    """Transcribe audio file to text"""
    # The service expects a file-like object with .read() method
    # UploadFile.file is a SpooledTemporaryFile which works with pydub
    request = GetTranscriptionRequest(audio=audio.file)
    return get_transcription(session, request)
