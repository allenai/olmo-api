from io import StringIO
from typing import IO, cast

import pytest
from flask_pydantic_api.utils import UploadedFile
from pydantic import ValidationError

from src.config.ModelConfig import ModelHost, ModelType, MultiModalModelConfig
from src.message.validate_message_files_from_config import validate_message_files_from_config


def create_model_config() -> MultiModalModelConfig:
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
        "accepts_files": None,
        "accepted_file_types": [],
        "max_files_per_message": None,
        "require_file_to_prompt": None,
        "max_total_file_size": None,
        "allow_files_in_followups": None,
    }

    return config


def test_error_if_files_present_but_doesnt_accept_files() -> None:
    model_config = create_model_config()
    model_config["accepts_files"] = False

    with pytest.raises(ValidationError) as e:
        validate_message_files_from_config([UploadedFile(cast(IO, StringIO("foo")))], model_config, has_parent=True)

    validation_errors = e.value.errors()
    assert len(validation_errors) == 1
    assert validation_errors[0]["msg"] == "This model doesn't accept files"
