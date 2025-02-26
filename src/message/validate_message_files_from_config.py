import os
from collections.abc import Sequence
from typing import Self

from flask_pydantic_api.utils import UploadedFile
from pydantic import BaseModel, Field, model_validator

from src.config.ModelConfig import FileRequiredToPromptOption, MultiModalModelConfig


def get_file_size(file: UploadedFile):
    file.stream.seek(0, os.SEEK_END)
    file_size = file.stream.tell()
    file.seek(0)

    return file_size


class CreateMessageRequestFilesValidator(BaseModel):
    files: Sequence[UploadedFile] | None = Field(default=None)
    has_parent: bool
    multi_modal_model_config: MultiModalModelConfig

    @model_validator(mode="after")
    def validate_no_files_when_not_accepted(self) -> Self:
        if (
            self.multi_modal_model_config["accepts_files"] is not True
            and self.files is not None
            and len(self.files) > 0
        ):
            error_message = "This model doesn't accept files"
            raise ValueError(error_message)

        return self

    @model_validator(mode="after")
    def validate_file_passed_when_required(self) -> Self:
        require_file_to_prompt = self.multi_modal_model_config["require_file_to_prompt"]
        are_files_present = self.files is not None and len(self.files) > 0

        if require_file_to_prompt is FileRequiredToPromptOption.NoRequirement or are_files_present:
            return self

        if require_file_to_prompt is FileRequiredToPromptOption.AllMessages and not are_files_present:
            error_message = "This model requires a file to be sent with all messages"
            raise ValueError(error_message)

        if (
            require_file_to_prompt is FileRequiredToPromptOption.FirstMessage
            and not are_files_present
            and not self.has_parent
        ):
            error_message = "This model requires a file to be sent with the first message"
            raise ValueError(error_message)

        return self

    @model_validator(mode="after")
    def validate_files_allowed_in_followups(self) -> Self:
        are_files_present = self.files is not None and len(self.files) > 0

        if not self.multi_modal_model_config["allow_files_in_followups"] and self.has_parent and are_files_present:
            error_message = "This model doesn't allow files to be sent in follow-up messages"
            raise ValueError(error_message)

        return self

    @model_validator(mode="after")
    def validate_files_dont_exceed_maximum(self) -> Self:
        max_files_per_message = self.multi_modal_model_config["max_files_per_message"]
        if max_files_per_message is not None and len(self.files or []) > max_files_per_message:
            error_message = f"This model only allows {max_files_per_message} files per message"
            raise ValueError(error_message)

        return self

    @model_validator(mode="after")
    def validate_max_total_file_size(self) -> Self:
        max_total_file_size = self.multi_modal_model_config["max_total_file_size"]

        if max_total_file_size is not None and self.files is not None:
            file_sizes = map(get_file_size, self.files)
            total_file_size = sum(file_sizes)

            if total_file_size > max_total_file_size:
                error_message = f"This model has a max total file size of {max_total_file_size}"
                raise ValueError(error_message)

        return self

    @model_validator(mode="after")
    def validate_allowed_file_types(self) -> Self:
        return self


def validate_message_files_from_config(
    request_files: Sequence[UploadedFile] | None, config: MultiModalModelConfig, *, has_parent: bool
):
    CreateMessageRequestFilesValidator(files=request_files, multi_modal_model_config=config, has_parent=has_parent)
