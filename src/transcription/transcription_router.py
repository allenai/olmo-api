"""
Transcription Router (FastAPI) - V4
------------------------------------

FastAPI router for audio transcription operations.
Converted from Flask blueprint in transcription_blueprint.py.
"""

import asyncio

from fastapi import APIRouter, File, UploadFile

from src.transcription.transcription_service import (
    GetTranscriptionRequest,
    GetTranscriptionResponse,
    TranscriptionServiceDep,
    get_transcription,
)

router = APIRouter(tags=["v4", "transcribe"])


@router.post("/", response_model=GetTranscriptionResponse)
async def transcribe(service: TranscriptionServiceDep, audio: UploadFile = File(...)) -> GetTranscriptionResponse:
    """Transcribe audio file to text"""
    # The service expects a file-like object with .read() method
    # UploadFile.file is a SpooledTemporaryFile which works with pydub
    request = GetTranscriptionRequest(audio=audio.file)
    return await asyncio.to_thread(service.get_transcription, request)
