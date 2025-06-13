from typing import IO, cast

from flask_pydantic_api.utils import UploadedFile
from pydub import AudioSegment
from sqlalchemy.orm import sessionmaker

from src.api_interface import APIInterface
from src.config.get_models import get_model_by_host_and_id
from src.constants import OLMO_ASR_MODEL_ID
from src.dao.message import Role
from src.inference.InferenceEngine import InferenceEngineMessage, InferenceOptions
from src.inference.olmo_asr_engine import OlmoAsrModalEngine


class GetTranscriptionRequest(APIInterface):
    audio: UploadedFile


class GetTranscriptionResponse(APIInterface):
    text: str


def get_transcription(request: GetTranscriptionRequest, session_maker: sessionmaker):
    # audio_bytes = request.audio.read()
    segment = AudioSegment.from_file_using_temporary_files(request.audio)
    # .export can return a path with different options but returns IO when we call it without a filename
    converted_audio_file = cast(IO, segment.export(format="wav"))

    olmo_asr_engine = OlmoAsrModalEngine()

    model = get_model_by_host_and_id(host="modal", id=OLMO_ASR_MODEL_ID, session_maker=session_maker)
    messages = [InferenceEngineMessage(role=Role.User, content="", files=[converted_audio_file.read()])]
    response = next(
        olmo_asr_engine.create_streamed_message(
            model=model.model_id_on_host, messages=messages, inference_options=InferenceOptions()
        )
    )

    return GetTranscriptionResponse(text=response.content)
