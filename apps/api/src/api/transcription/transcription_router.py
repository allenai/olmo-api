from fastapi import APIRouter, UploadFile

from api.transcription.transcription_service import (
    TranscriptionServiceDependency,
)
from core import APIInterface

transcription_router = APIRouter(prefix="/transcription")


class TranscriptionSingleResponse(APIInterface):
    text: str


@transcription_router.post("/single")
async def transcribe(
    audio: UploadFile, transcription_service: TranscriptionServiceDependency
) -> TranscriptionSingleResponse:
    text = await transcription_service.transcribe_single(audio=audio.file)
    return TranscriptionSingleResponse(text=text)
