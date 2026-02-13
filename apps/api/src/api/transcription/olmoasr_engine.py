from typing import Annotated, BinaryIO, Final

import modal
from fastapi import Depends

OLMO_ASR_MODEL_CONFIG_ID: Final[str] = "olmoasr"


class OlmoAsrEngine:
    @staticmethod
    async def transcribe(app_name: str, audio: BinaryIO) -> str:
        modal_class = modal.Cls.from_name(app_name=app_name, name="Model")

        transcription_result = await modal_class().transcribe.remote.aio(audio=audio.read())
        return transcription_result.get("text")


OlmoAsrEngineDependency = Annotated[OlmoAsrEngine, Depends()]
