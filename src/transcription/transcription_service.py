from time import time_ns
from typing import IO, Annotated, cast

from fastapi import Depends
from pydub import AudioSegment  # type: ignore
from pydantic import ConfigDict
from sqlalchemy.orm import Session

from src.api_interface import APIInterface
from src.config.get_models import get_model_by_host_and_id
from src.constants import OLMO_ASR_MODEL_ID
from src.dao.message.message_models import Role
from src.dependencies import DBSession
from src.inference.InferenceEngine import InferenceEngineMessage, InferenceOptions
from src.inference.olmo_asr_engine import OlmoAsrModalEngine
from src.message.inference_logging import log_inference_timing
from src.message.validate_message_files_from_config import get_file_size
from src.uploaded_file import UploadedFile


class GetTranscriptionRequest(APIInterface):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    audio: UploadedFile


class GetTranscriptionResponse(APIInterface):
    text: str


def get_transcription(session: Session, request: GetTranscriptionRequest):
    start_all_ns = time_ns()
    segment = AudioSegment.from_file_using_temporary_files(request.audio)

    # .export can return a path with different options but returns IO when we call it without a filename
    converted_audio_file = cast(IO, segment.export(format="wav"))

    olmo_asr_engine = OlmoAsrModalEngine()

    model = get_model_by_host_and_id(session, host="modal", id=OLMO_ASR_MODEL_ID)
    messages = [InferenceEngineMessage(role=Role.User, content="", files=[converted_audio_file.read()])]

    start_generation_ns = time_ns()
    response = next(
        olmo_asr_engine.create_streamed_message(
            model=model.model_id_on_host, messages=messages, inference_options=InferenceOptions()
        )
    )
    first_ns = time_ns()
    end_all_ns = time_ns()

    log_inference_timing(
        "transcribe",
        ttft_ns=(first_ns - start_generation_ns),
        total_ns=(end_all_ns - start_all_ns),
        input_token_count=response.input_token_count,
        output_token_count=response.output_token_count,
        model=OLMO_ASR_MODEL_ID,
        file_size=get_file_size(request.audio),
    )

    return GetTranscriptionResponse(text=response.content)


# Service class with dependency injection
class TranscriptionService:
    """
    Transcription service with dependency-injected database session.

    This service encapsulates transcription operations and receives
    its dependencies through constructor injection.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_transcription(self, request: GetTranscriptionRequest):
        """Transcribe audio file to text"""
        start_all_ns = time_ns()
        segment = AudioSegment.from_file_using_temporary_files(request.audio)

        # .export can return a path with different options but returns IO when we call it without a filename
        converted_audio_file = cast(IO, segment.export(format="wav"))

        olmo_asr_engine = OlmoAsrModalEngine()

        model = get_model_by_host_and_id(self.session, host="modal", id=OLMO_ASR_MODEL_ID)
        messages = [InferenceEngineMessage(role=Role.User, content="", files=[converted_audio_file.read()])]

        start_generation_ns = time_ns()
        response = next(
            olmo_asr_engine.create_streamed_message(
                model=model.model_id_on_host, messages=messages, inference_options=InferenceOptions()
            )
        )
        first_ns = time_ns()
        end_all_ns = time_ns()

        log_inference_timing(
            "transcribe",
            ttft_ns=(first_ns - start_generation_ns),
            total_ns=(end_all_ns - start_all_ns),
            input_token_count=response.input_token_count,
            output_token_count=response.output_token_count,
            model=OLMO_ASR_MODEL_ID,
            file_size=get_file_size(request.audio),
        )

        return GetTranscriptionResponse(text=response.content)


def get_transcription_service(session: DBSession) -> TranscriptionService:
    """Dependency provider for TranscriptionService"""
    return TranscriptionService(session)


# Type alias for dependency injection
TranscriptionServiceDep = Annotated[TranscriptionService, Depends(get_transcription_service)]
