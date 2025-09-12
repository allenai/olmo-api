from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import time_machine

from src.config.Model import Model
from src.dao.engine_models.model_config import ModelHost, ModelType, PromptType


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_not_visible_when_not_available_yet() -> None:
    model = Model.model_validate({
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
        "prompt_type": PromptType.TEXT_ONLY,
    })

    assert model.is_deprecated is True
    assert model.is_visible is False


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_not_visible_when_past_deprecated_time() -> None:
    model = Model.model_validate({
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
        "prompt_type": PromptType.TEXT_ONLY,
    })

    assert model.is_deprecated is True
    assert model.is_visible is False


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_not_visible_when_past_deprecated_time_and_available_time() -> None:
    model = Model.model_validate({
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
        "prompt_type": PromptType.TEXT_ONLY,
    })

    assert model.is_deprecated is True
    assert model.is_visible is False


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_visible_when_past_available_time() -> None:
    model = Model.model_validate({
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
        "prompt_type": PromptType.TEXT_ONLY,
    })

    assert model.is_deprecated is False
    assert model.is_visible is True


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_visible_when_no_available_time() -> None:
    model = Model.model_validate({
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
        "prompt_type": PromptType.TEXT_ONLY,
    })

    assert model.is_deprecated is False
    assert model.is_visible is True


@time_machine.travel(datetime(2025, 1, 1, tzinfo=UTC))
def test_is_visible_when_deprecation_time_is_in_the_future() -> None:
    model = Model.model_validate({
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
        "prompt_type": PromptType.TEXT_ONLY,
    })

    assert model.is_deprecated is False
    assert model.is_visible is True


def test_converts_times_to_utc() -> None:
    model = Model.model_validate({
        "id": "foo",
        "name": "foo",
        "host": ModelHost.Modal,
        "description": "desc",
        "compute_source_id": "csid",
        "model_type": ModelType.Chat,
        "system_prompt": None,
        "family_id": None,
        "family_name": None,
        "available_time": datetime(2025, 1, 1).astimezone(ZoneInfo("America/New_York")).isoformat(),
        "deprecation_time": datetime(2026, 1, 1).astimezone(ZoneInfo("America/Los_Angeles")).isoformat(),
        "internal": False,
        "prompt_type": PromptType.TEXT_ONLY,
    })
    assert model.available_time is not None
    assert model.available_time.tzname() == "UTC"

    assert model.deprecation_time is not None
    assert model.deprecation_time.tzname() == "UTC"
