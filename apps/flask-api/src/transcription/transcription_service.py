from time import time_ns
from typing import IO, cast

from pydub import AudioSegment  # type: ignore

from core.api_interface import APIInterface
from src.config.get_models import get_model_by_id
from src.constants import OLMO_ASR_MODEL_ID
from src.dao.message.message_models import Role
from src.flask_pydantic_api.utils import UploadedFile
from src.inference.InferenceEngine import InferenceEngineMessage, InferenceOptions
from src.inference.olmo_asr_engine import OlmoAsrModalEngine
from src.message.inference_logging import log_inference_timing
from src.message.validate_message_files_from_config import get_file_size


class GetTranscriptionRequest(APIInterface):
    audio: UploadedFile


class GetTranscriptionResponse(APIInterface):
    text: str


def get_transcription(request: GetTranscriptionRequest):
    start_all_ns = time_ns()
    segment = AudioSegment.from_file_using_temporary_files(request.audio)

    # .export can return a path with different options but returns IO when we call it without a filename
    converted_audio_file = cast(IO, segment.export(format="wav"))

    olmo_asr_engine = OlmoAsrModalEngine()

    model = get_model_by_id(id=OLMO_ASR_MODEL_ID)
    messages = [InferenceEngineMessage(role=Role.User, content="", files=[converted_audio_file.read()])]

    start_generation_ns = time_ns()
    response = next(
        olmo_asr_engine.create_streamed_message(
            model=model.model_id_on_host,
            messages=messages,
            inference_options=InferenceOptions(),
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
