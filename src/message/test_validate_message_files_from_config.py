from io import StringIO
from typing import IO, Any, Optional, cast

import pytest
from flask_pydantic_api.utils import UploadedFile
from pydantic import ValidationError

from src.config.ModelConfig import FileRequiredToPromptOption, ModelHost, ModelType, MultiModalModelConfig
from src.message.validate_message_files_from_config import validate_message_files_from_config


def create_model_config(
    # Allowing dict[str, Any] keeps autocomplete but gets the typing to stop yelling at us if we don't have the entire dict
    partial_config: Optional[MultiModalModelConfig | dict[str, Any]] = None,
) -> MultiModalModelConfig:
    config: MultiModalModelConfig = {
        "id": "id",
        "name": "name",
        "host": ModelHost.InferD,
        "description": "description",
        "compute_source_id": "compute_source_id",
        "model_type": ModelType.Chat,
        "system_prompt": None,
        "family_id": None,
        "family_name": None,
        "available_time": None,
        "deprecation_time": None,
        "accepts_files": True,
        "accepted_file_types": [],
        "max_files_per_message": None,
        "require_file_to_prompt": None,
        "max_total_file_size": None,
        "allow_files_in_followups": None,
    }

    if partial_config is not None:
        config.update(cast(MultiModalModelConfig, partial_config))

    return config


@pytest.mark.parametrize(
    ("model_config", "has_parent", "error_message", "uploaded_file_count"),
    [
        pytest.param(
            create_model_config({
                "allow_files_in_followups": False,
            }),
            True,
            "This model doesn't allow files to be sent in follow-up messages",
            1,
            id="no follow-up files allowed",
        ),
        pytest.param(
            create_model_config({"require_file_to_prompt": FileRequiredToPromptOption.FirstMessage}),
            False,
            "This model requires a file to be sent with the first message",
            0,
            id="file required with first message",
        ),
        pytest.param(
            create_model_config({"require_file_to_prompt": FileRequiredToPromptOption.AllMessages}),
            False,
            "This model requires a file to be sent with all messages",
            0,
            id="file required with first message when required in all messages",
        ),
        pytest.param(
            create_model_config({"require_file_to_prompt": FileRequiredToPromptOption.AllMessages}),
            True,
            "This model requires a file to be sent with all messages",
            0,
            id="file required with first message when required in all messages",
        ),
        pytest.param(
            create_model_config({"max_files_per_message": 2}),
            False,
            "This model only allows 2 files per message",
            3,
            id="too many files",
        ),
    ],
)
def test_file_validation_errors(model_config, has_parent: bool, error_message: str, uploaded_file_count: int):  # noqa: FBT001
    uploaded_files = [UploadedFile(cast(IO, StringIO("foo")))] * uploaded_file_count

    with pytest.raises(ValidationError, match=error_message):
        validate_message_files_from_config(uploaded_files, model_config, has_parent=has_parent)


@pytest.mark.parametrize(
    ("model_config", "has_parent", "uploaded_file_count"),
    [
        pytest.param(
            create_model_config({
                "allow_files_in_followups": False,
            }),
            True,
            0,
            id="not sending a follow-up file when not allowed",
        ),
        pytest.param(
            create_model_config({"require_file_to_prompt": FileRequiredToPromptOption.FirstMessage}),
            False,
            1,
            id="send a file with the first message when required",
        ),
        pytest.param(
            create_model_config({"require_file_to_prompt": FileRequiredToPromptOption.AllMessages}),
            False,
            1,
            id="send a file when required on all messages",
        ),
        pytest.param(
            create_model_config({
                "require_file_to_prompt": FileRequiredToPromptOption.AllMessages,
                "allow_files_in_followups": True,
            }),
            True,
            1,
            id="send a file with a child message when required on all messages",
        ),
        pytest.param(
            create_model_config({"max_files_per_message": 2}),
            False,
            2,
            id="send the max amount of files",
        ),
    ],
)
def test_file_validation_passes(model_config, has_parent: bool, uploaded_file_count: int):  # noqa: FBT001
    uploaded_files = [UploadedFile(cast(IO, StringIO("foo")))] * uploaded_file_count
    validate_message_files_from_config(uploaded_files, config=model_config, has_parent=has_parent)
