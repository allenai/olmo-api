import os
from collections.abc import Sequence
from datetime import UTC, datetime
from io import StringIO
from typing import IO, Any, cast

import pytest
from flask_pydantic_api.utils import UploadedFile
from pydantic import ValidationError

from src.dao.engine_models.model_config import (
    FileRequiredToPromptOption,
    ModelConfig,
    ModelHost,
    ModelType,
    MultiModalModelConfig,
    PromptType,
)
from src.message.validate_message_files_from_config import validate_message_files_from_config


def create_model_config(
    partial_config: dict[str, Any] | None = None,
) -> ModelConfig | MultiModalModelConfig:
    values = {
        "id": "id",
        "name": "name",
        "host": ModelHost.InferD,
        "description": "description",
        "model_id_on_host": "compute_source_id",
        "model_type": ModelType.Chat,
        "internal": False,
        "default_system_prompt": None,
        "family_id": None,
        "family_name": None,
        "available_time": None,
        "deprecation_time": None,
        "prompt_type": PromptType.MULTI_MODAL,
        "accepted_file_types": [],
        "max_files_per_message": None,
        "require_file_to_prompt": FileRequiredToPromptOption.NoRequirement,
        "max_total_file_size": None,
        "allow_files_in_followups": False,
    }

    if partial_config is not None:
        values.update(partial_config)

    model_config = MultiModalModelConfig(**values)  # type: ignore
    model_config.order = 0
    model_config.created_time = datetime.now(UTC)
    model_config.updated_time = datetime.now(UTC)

    return model_config


def create_uploaded_files(count: int) -> Sequence[UploadedFile]:
    return [UploadedFile(cast(IO, StringIO("foo")))] * count


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
        pytest.param(
            create_model_config({"max_total_file_size": "2B"}),
            False,
            "This model has a max total file size of 2B",
            1,
            id="files too large",
        ),
    ],
)
def test_file_validation_errors(model_config, has_parent: bool, error_message: str, uploaded_file_count: int):  # noqa: FBT001
    uploaded_files = create_uploaded_files(uploaded_file_count)

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
        pytest.param(
            create_model_config({"max_files_per_message": 2}),
            False,
            1,
            id="send below the max amount of files",
        ),
        pytest.param(
            create_model_config({"require_file_to_prompt": FileRequiredToPromptOption.NoRequirement}),
            False,
            0,
            id="send no files when not required",
        ),
    ],
)
def test_file_validation_passes(model_config: MultiModalModelConfig, has_parent: bool, uploaded_file_count: int):  # noqa: FBT001
    uploaded_files = create_uploaded_files(uploaded_file_count)

    validate_message_files_from_config(uploaded_files, config=model_config, has_parent=has_parent)


def test_file_validation_fails_if_a_file_is_sent_to_a_non_multi_modal_model() -> None:
    uploaded_files = create_uploaded_files(1)
    model_config = ModelConfig(
        id="id",
        host=ModelHost.Modal,
        name="name",
        description="description",
        model_id_on_host="compute_source_id",
        model_type=ModelType.Chat,
        prompt_type=PromptType.TEXT_ONLY,
        internal=False,
    )

    with pytest.raises(ValidationError, match=""):
        validate_message_files_from_config(request_files=uploaded_files, config=model_config, has_parent=False)


def test_file_validation_fails_if_a_file_type_is_not_allowed() -> None:
    model_config = create_model_config({"accepted_file_types": ["application/pdf", "image/jpg"]})
    with open(os.path.join(os.path.dirname(__file__), "file_validation", "test-small-png.png"), "rb") as f:
        uploaded_file = UploadedFile(stream=f)

        with pytest.raises(
            ValidationError, match=r"This model only accepts files of types \['application/pdf', 'image/jpg'\]"
        ):
            validate_message_files_from_config(request_files=[uploaded_file], config=model_config, has_parent=False)


def test_file_validation_passes_if_a_file_type_is_allowed() -> None:
    model_config = create_model_config({"accepted_file_types": ["application/pdf", "image/png"]})
    with open(os.path.join(os.path.dirname(__file__), "file_validation", "test-small-png.png"), "rb") as f:
        uploaded_file = UploadedFile(stream=f)

        validate_message_files_from_config(request_files=[uploaded_file], config=model_config, has_parent=False)
