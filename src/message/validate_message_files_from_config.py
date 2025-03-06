import os
from collections.abc import Sequence
from typing import Self

from flask_pydantic_api.utils import UploadedFile
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.config.Model import Model, MultiModalModel
from src.config.ModelConfig import FileRequiredToPromptOption
from src.message.file_validation.check_is_file_in_allowed_file_types import check_is_file_in_allowed_file_types


def get_file_size(file: UploadedFile):
    file.stream.seek(0, os.SEEK_END)
    file_size = file.stream.tell()
    file.seek(0)

    return file_size


# Using a Pydantic model to validate lets us easily create a ValidationError
class CreateMessageRequestFilesValidator(BaseModel):
    files: Sequence[UploadedFile] | None = Field(default=None)
    has_parent: bool
    # named with our_ in front so it doesn't conflict with pydantic's model_config
    our_model_config: MultiModalModel

    model_config = ConfigDict(hide_input_in_errors=True)

    @model_validator(mode="after")
    def validate_no_files_when_not_accepted(self) -> Self:
        if self.our_model_config.accepts_files is not True and self.files is not None and len(self.files) > 0:
            error_message = "This model doesn't accept files"
            raise ValueError(error_message)

        return self

    @model_validator(mode="after")
    def validate_file_passed_when_required(self) -> Self:
        require_file_to_prompt = self.our_model_config.require_file_to_prompt
        are_files_present = self.files is not None and len(self.files) > 0

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

        if not self.our_model_config.allow_files_in_followups and self.has_parent and are_files_present:
            error_message = "This model doesn't allow files to be sent in follow-up messages"
            raise ValueError(error_message)

        return self

    @model_validator(mode="after")
    def validate_files_dont_exceed_maximum(self) -> Self:
        max_files_per_message = self.our_model_config.max_files_per_message
        if max_files_per_message is not None and len(self.files or []) > max_files_per_message:
            error_message = f"This model only allows {max_files_per_message} files per message"
            raise ValueError(error_message)

        return self

    @model_validator(mode="after")
    def validate_max_total_file_size(self) -> Self:
        max_total_file_size = self.our_model_config.max_total_file_size

        if max_total_file_size is not None and self.files is not None:
            file_sizes = map(get_file_size, self.files)
            total_file_size = sum(file_sizes)

            if total_file_size > max_total_file_size:
                error_message = (
                    f"This model has a max total file size of {max_total_file_size.human_readable(decimal=True)}"
                )
                raise ValueError(error_message)

        return self

    @model_validator(mode="after")
    def validate_allowed_file_types(self) -> Self:
        if self.files is None:
            return self

        do_files_match_allowed_file_types = all(
            check_is_file_in_allowed_file_types(file.stream, self.our_model_config.accepted_file_types)
            for file in self.files
        )

        if not do_files_match_allowed_file_types:
            error_message = f"This model only accepts files of types {self.our_model_config.accepted_file_types}"
            raise ValueError(error_message)
        return self


def validate_message_files_from_config(
    request_files: Sequence[UploadedFile] | None, config: Model, *, has_parent: bool
):
    if isinstance(config, MultiModalModel):
        CreateMessageRequestFilesValidator(files=request_files, our_model_config=config, has_parent=has_parent)
    else:
        CreateMessageRequestFilesValidator(
            files=request_files,
            our_model_config=MultiModalModel.model_construct(**config.model_dump()),
            has_parent=has_parent,
        )
