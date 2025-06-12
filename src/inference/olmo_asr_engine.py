from collections.abc import Generator, Sequence

import modal
from werkzeug.exceptions import BadRequest

from src.config.get_config import get_config
from src.inference.InferenceEngine import (
    InferenceEngine,
    InferenceEngineChunk,
    InferenceEngineMessage,
    InferenceOptions,
)


class OlmoAsrModalEngine(InferenceEngine):
    client: modal.Client

    def __init__(self) -> None:
        cfg = get_config()
        self.client = modal.Client.from_credentials(cfg.modal.token, cfg.modal.token_secret)

    def create_streamed_message(
        self,
        model: str,
        messages: Sequence[InferenceEngineMessage],
        inference_options: InferenceOptions,  # noqa: ARG002
    ) -> Generator[InferenceEngineChunk, None, None]:
        modal_class = modal.Cls.from_name(model, "Model").hydrate(client=self.client)()

        files = next(message.files for message in messages)

        if files is None or len(files) == 0:
            missing_files_message = "Tried to transcribe a message without a file in the first message"
            raise BadRequest(missing_files_message)

        audio = next(file for file in files)

        if isinstance(audio, str):
            # TODO: this is a file url, maybe we should handle this in the future?
            no_saved_file_message = "Tried to transcribe a message that had a previously uploaded file"
            raise BadRequest(no_saved_file_message)

        transcription_result = modal_class.transcribe.remote(audio=audio.read())

        yield InferenceEngineChunk(content=transcription_result.get("text"), model=model)
