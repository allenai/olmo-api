from datetime import UTC, datetime

import time_machine

from src.config.Model import map_model_from_config
from src.config.ModelConfig import ModelConfig, ModelHost, ModelType


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_not_visible_when_not_available_yet() -> None:
    test_model_config: ModelConfig = {
        "id": "foo",
        "name": "foo",
        "host": ModelHost.Modal,
        "description": "desc",
        "compute_source_id": "csid",
        "model_type": ModelType.Chat,
        "available_time": datetime(2025, 1, 2).astimezone(UTC).isoformat(),
        "system_prompt": None,
        "family_id": None,
        "family_name": None,
        "deprecation_time": None,
        "internal": False,
    }

    model = map_model_from_config(test_model_config)

    assert model.is_deprecated is True
    assert model.is_visible is False


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_not_visible_when_past_deprecated_time() -> None:
    test_model_config: ModelConfig = {
        "id": "foo",
        "name": "foo",
        "host": ModelHost.Modal,
        "description": "desc",
        "compute_source_id": "csid",
        "model_type": ModelType.Chat,
        "available_time": None,
        "system_prompt": None,
        "family_id": None,
        "family_name": None,
        "deprecation_time": datetime(2024, 1, 1).astimezone(UTC).isoformat(),
        "internal": False,
    }

    model = map_model_from_config(test_model_config)

    assert model.is_deprecated is True
    assert model.is_visible is False


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_not_visible_when_past_deprecated_time_and_available_time() -> None:
    test_model_config: ModelConfig = {
        "id": "foo",
        "name": "foo",
        "host": ModelHost.Modal,
        "description": "desc",
        "compute_source_id": "csid",
        "model_type": ModelType.Chat,
        "available_time": datetime(2023, 1, 1).astimezone(UTC).isoformat(),
        "system_prompt": None,
        "family_id": None,
        "family_name": None,
        "deprecation_time": datetime(2024, 1, 1).astimezone(UTC).isoformat(),
        "internal": False,
    }

    model = map_model_from_config(test_model_config)

    assert model.is_deprecated is True
    assert model.is_visible is False


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_visible_when_past_available_time() -> None:
    test_model_config: ModelConfig = {
        "id": "foo",
        "name": "foo",
        "host": ModelHost.Modal,
        "description": "desc",
        "compute_source_id": "csid",
        "model_type": ModelType.Chat,
        "available_time": datetime(2023, 1, 1).astimezone(UTC).isoformat(),
        "system_prompt": None,
        "family_id": None,
        "family_name": None,
        "deprecation_time": None,
        "internal": False,
    }

    model = map_model_from_config(test_model_config)

    assert model.is_deprecated is False
    assert model.is_visible is True


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_visible_when_no_available_time() -> None:
    test_model_config: ModelConfig = {
        "id": "foo",
        "name": "foo",
        "host": ModelHost.Modal,
        "description": "desc",
        "compute_source_id": "csid",
        "model_type": ModelType.Chat,
        "available_time": None,
        "system_prompt": None,
        "family_id": None,
        "family_name": None,
        "deprecation_time": None,
        "internal": False,
    }

    model = map_model_from_config(test_model_config)

    assert model.is_deprecated is False
    assert model.is_visible is True


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_visible_when_deprecation_time_is_in_the_future() -> None:
    test_model_config: ModelConfig = {
        "id": "foo",
        "name": "foo",
        "host": ModelHost.Modal,
        "description": "desc",
        "compute_source_id": "csid",
        "model_type": ModelType.Chat,
        "available_time": None,
        "system_prompt": None,
        "family_id": None,
        "family_name": None,
        "deprecation_time": datetime(2026, 1, 1).astimezone(UTC).isoformat(),
        "internal": False,
    }

    model = map_model_from_config(test_model_config)

    assert model.is_deprecated is False
    assert model.is_visible is True
