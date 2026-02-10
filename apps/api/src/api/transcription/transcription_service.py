import asyncio
from typing import Annotated, BinaryIO

from fastapi import Depends
from pydub import AudioSegment

from api.model_config.admin.model_config_admin_read_service import ModelConfigAdminReadServiceDependency
from api.transcription.olmoasr_engine import OLMO_ASR_MODEL_CONFIG_ID, OlmoAsrEngineDependency


class TranscriptionService:
    def __init__(
        self, model_config_read_service: ModelConfigAdminReadServiceDependency, olmoasr_engine: OlmoAsrEngineDependency
    ):
        self.model_config_read_service = model_config_read_service
        self.olmoasr_engine = olmoasr_engine

    async def transcribe_single(self, audio: BinaryIO) -> str:
        olmo_asr_config = await self.model_config_read_service.get_one(OLMO_ASR_MODEL_CONFIG_ID)

        if olmo_asr_config is None:
            model_config_not_found = "OlmoASR model config not found"
            raise ValueError(model_config_not_found)

        converted_audio = await asyncio.to_thread(self.convert_to_wav, audio=audio)

        text = await self.olmoasr_engine.transcribe(
            app_name=olmo_asr_config.root.model_id_on_host,
            audio=converted_audio,
        )

        return text

    @staticmethod
    def convert_to_wav(audio: BinaryIO) -> BinaryIO:
        segment = AudioSegment.from_file(audio)
        buffer = segment.export(format="wav")
        buffer.seek(0)
        return buffer


TranscriptionServiceDependency = Annotated[TranscriptionService, Depends()]
