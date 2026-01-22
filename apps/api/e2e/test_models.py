import operator
from typing import cast
from uuid import uuid4

from pydantic import HttpUrl
import pytest
from httpx import AsyncClient

from api.model_config.admin.model_config_admin_create_service import (
    CreateMultiModalModelConfigRequest,
    CreateTextOnlyModelConfigRequest,
)
from api.model_config.admin.model_config_admin_update_service import (
    UpdateMultiModalModelConfigRequest,
    UpdateTextOnlyModelConfigRequest,
)
from api.model_config.model_config_response import (
    AvailableInfiniGramIndexId,
    ModelConfigListResponse,
    ModelConfigResponse,
    MultiModalModelConfigResponse,
)
from db.models.model_config import ModelHost, ModelType, PromptType
from e2e.conftest import AuthenticatedClient, auth_headers_for_user

PUBLIC_MODEL_ENDPOINT = "/v5/models/"
ADMIN_MODEL_CONFIG_ENDPOINT = "/v5/admin/models/"

default_inference_constraints = {
    "max_tokens_default": 2048,
    "max_tokens_upper": 2048,
    "max_tokens_lower": 1,
    "max_tokens_step": 1,
    "temperature_default": 0.7,
    "temperature_upper": 1.0,
    "temperature_lower": 0.0,
    "temperature_step": 0.01,
    "top_p_default": 1.0,
    "top_p_upper": 1.0,
    "top_p_lower": 0.0,
    "top_p_step": 0.01,
    "stop_default": None,
}


async def list_admin_models(
    client: AsyncClient,
    user: AuthenticatedClient,
) -> list[dict]:
    response = await client.get(
        ADMIN_MODEL_CONFIG_ENDPOINT,
        headers=auth_headers_for_user(user),
    )
    response.raise_for_status()
    return response.json()


async def list_public_models(
    client: AsyncClient,
    user: AuthenticatedClient,
) -> list[dict]:
    response = await client.get(
        PUBLIC_MODEL_ENDPOINT,
        headers=auth_headers_for_user(user),
    )
    response.raise_for_status()
    return response.json()


# TODO: Implement skipped tests from from flask-api
#
@pytest.mark.skip(reason="Public endpoint not yet implemented")
async def test_get_public_models():
    # public models from {PUBLIC_MODEL_ENDPOINT}
    pass


@pytest.mark.skip(reason="Public endpoint not yet implemented")
async def test_get_internal_models():
    # internal models from {PUBLIC_MODEL_ENDPOINT}
    # can maybe combine with above?
    pass


async def test_get_admin_models_should_be_forbidden(client: AsyncClient, anon_user: AuthenticatedClient):
    response = await client.get(
        ADMIN_MODEL_CONFIG_ENDPOINT,
        headers=auth_headers_for_user(anon_user),
    )

    assert response.status_code == 401


async def test_get_admin_models(client: AsyncClient, auth_user: AuthenticatedClient):
    response = await list_admin_models(client, auth_user)

    if isinstance(response, list):
        # should have at least one model entity
        assert len(response) > 0

        # should have the following fields that match the model response
        entity = response[0]
        assert "is_visible" not in entity
        assert "host" in entity
        assert "modelIdOnHost" in entity
        assert "availableTime" in entity
        assert "deprecationTime" in entity
    else:
        msg = f"Response returned from GET {ADMIN_MODEL_CONFIG_ENDPOINT} was not a list"
        raise TypeError(msg)


async def test_create_text_only_model(
    client: AsyncClient,
    auth_user: AuthenticatedClient,
):
    model_id = f"test-model-{uuid4()}"
    create_model_request = CreateTextOnlyModelConfigRequest(
        id=model_id,
        name="model made for testing",
        description="This model is made for testing",
        model_id_on_host="test-model-id",
        information_url=HttpUrl("https://google.com"),
        model_type=ModelType.Chat,
        host=ModelHost.BeakerQueues,
        prompt_type=PromptType.TEXT_ONLY,
        can_think=True,
    )

    create_response = await client.post(
        ADMIN_MODEL_CONFIG_ENDPOINT,
        json=create_model_request.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    create_response.raise_for_status()

    created_model = create_response.json()
    assert created_model["id"] == model_id
    assert created_model["createdTime"] is not None
    assert created_model["modelType"] == "chat"
    assert created_model["canThink"] is True
    assert created_model["temperatureDefault"] == default_inference_constraints["temperature_default"]
    assert created_model["topPDefault"] == default_inference_constraints["top_p_default"]
    assert created_model["maxTokensDefault"] == default_inference_constraints["max_tokens_default"]
    assert created_model["stopDefault"] == default_inference_constraints["stop_default"]

    # Verify model appears in list
    available_models = await list_admin_models(client, auth_user)
    test_model = next((model for model in available_models if model["id"] == model_id), None)
    assert test_model is not None, "The test model wasn't returned from the GET request"


async def test_create_multi_model_model(
    client: AsyncClient,
    auth_user: AuthenticatedClient,
):
    model_id = f"test-mm-model-{uuid4()}"
    create_model_request = CreateMultiModalModelConfigRequest(
        id=model_id,
        name="multi-modal model made for testing",
        description="This model is made for testing",
        model_id_on_host="test-mm-model-id",
        model_type=ModelType.Chat,
        host=ModelHost.InferD,
        prompt_type=PromptType.MULTI_MODAL,
        accepted_file_types=["image/*"],
        max_files_per_message=1,
        allow_files_in_followups=False,
    )

    create_response = await client.post(
        ADMIN_MODEL_CONFIG_ENDPOINT,
        json=create_model_request.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    create_response.raise_for_status()

    created_model = create_response.json()
    assert created_model.get("createdTime") is not None
    assert created_model.get("modelType") == "chat"

    # Flask test used public model endpoint
    # TODO: maybe switch back?
    available_models = await list_admin_models(client, auth_user)
    test_model = next((model for model in available_models if model.get("id") == model_id), None)

    assert test_model is not None, "The test model wasn't returned from the GET request"
    assert "image/*" in test_model.get("acceptedFileTypes", [])
    assert test_model.get("maxFilesPerMessage") == 1
    assert test_model.get("allowFilesInFollowups") is False


async def test_create_model_with_toolcalling(
    client: AsyncClient,
    auth_user: AuthenticatedClient,
):
    model_id = f"test-tool-model-{uuid4()}"
    create_model_request = CreateTextOnlyModelConfigRequest(
        id=model_id,
        name="model made for testing",
        description="This model is made for testing",
        model_id_on_host="test-model-id",
        model_type=ModelType.Chat,
        host=ModelHost.InferD,
        prompt_type=PromptType.TEXT_ONLY,
        can_call_tools=True,
    )

    create_response = await client.post(
        ADMIN_MODEL_CONFIG_ENDPOINT,
        json=create_model_request.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    create_response.raise_for_status()

    created_model = ModelConfigResponse.model_validate(create_response.json())
    assert created_model.root.created_time is not None
    assert created_model.root.model_type == ModelType.Chat
    assert created_model.root.can_call_tools is True

    available_models = await list_admin_models(client, auth_user)
    available_models_validated = ModelConfigListResponse.model_validate(available_models)

    test_admin_model = next(
        (model for model in available_models_validated.root if model.root.id == model_id),
        None,
    )
    assert test_admin_model is not None, "The test model wasn't returned from the GET request"
    assert test_admin_model.root.can_call_tools is True

    # Roughly:
    #
    # public_models = ModelListResponse.model_validate(await list_public_models(client, auth_user))
    # test_model = next((model for model in public_models.root if model.id == model_id), None)
    # assert test_model is not None, "The test model wasn't returned from the public endpoint"
    # assert test_model.can_call_tools is True
    # assert test_model.available_tools is not None, "Available tools weren't set on a tool-calling model"
    # assert len(test_model.available_tools) > 0


async def test_create_a_model_with_an_infini_gram_index(
    client: AsyncClient,
    auth_user: AuthenticatedClient,
):
    model_id = f"test-tool-model-{uuid4()}"
    create_model_request = CreateTextOnlyModelConfigRequest(
        id=model_id,
        name="model made for testing",
        description="This model is made for testing",
        model_id_on_host="test-model-id",
        model_type=ModelType.Chat,
        host=ModelHost.InferD,
        prompt_type=PromptType.TEXT_ONLY,
        infini_gram_index=AvailableInfiniGramIndexId.OLMO_2_0325_32B,
    )

    create_response = await client.post(
        ADMIN_MODEL_CONFIG_ENDPOINT,
        json=create_model_request.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    create_response.raise_for_status()

    created_model = ModelConfigResponse.model_validate(create_response.json()).root
    assert created_model.created_time is not None
    assert created_model.model_type == "chat"
    assert created_model.infini_gram_index == AvailableInfiniGramIndexId.OLMO_2_0325_32B

    available_models = await list_admin_models(client, auth_user)

    test_model = ModelConfigResponse.model_validate(
        next((model for model in available_models if model.get("id") == model_id), None)
    )
    assert test_model.root is not None, "The test model wasn't returned from the GET request"
    assert created_model.infini_gram_index == AvailableInfiniGramIndexId.OLMO_2_0325_32B


async def test_should_update_a_text_only_model(client: AsyncClient, auth_user: AuthenticatedClient):
    model_id = f"test-model-{uuid4()}"

    create_model_request = CreateTextOnlyModelConfigRequest(
        id=model_id,
        name="model made for testing",
        description="This model is made for testing",
        model_id_on_host="test-model-id",
        model_type=ModelType.Chat,
        host=ModelHost.InferD,
        prompt_type=PromptType.TEXT_ONLY,
    )

    create_response = await client.post(
        ADMIN_MODEL_CONFIG_ENDPOINT,
        json=create_model_request.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    create_response.raise_for_status()

    new_constraints = {
        "temperature_default": 0,  # ensure falsy value updates correctly
        "top_p_default": 0.9,
        "max_tokens_default": 1024,
        "stop_default": ["stop1", "stop2"],
    }

    update_model_request = UpdateTextOnlyModelConfigRequest(
        name="updated model made for testing",
        description="This model is made for testing",
        model_id_on_host="test-model-id",
        model_type=ModelType.Base,
        host=ModelHost.Modal,
        prompt_type=PromptType.TEXT_ONLY,
        can_call_tools=True,
        can_think=True,
        infini_gram_index=AvailableInfiniGramIndexId.OLMO_2_0325_32B,
        **new_constraints,
    )
    update_model_response = await client.put(
        f"{ADMIN_MODEL_CONFIG_ENDPOINT}{model_id}",
        json=update_model_request.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    update_model_response.raise_for_status()
    assert update_model_response.status_code == 200

    available_models = await list_admin_models(client, auth_user)

    updated_model = next(filter(lambda model: model.get("id") == model_id, available_models))
    assert updated_model is not None, "Updated model not returned from models endpoint"

    parsed_updated_model = ModelConfigResponse.model_validate(updated_model)

    assert parsed_updated_model.root.name == "updated model made for testing"
    assert parsed_updated_model.root.model_type == "base"
    assert parsed_updated_model.root.can_call_tools is True
    assert parsed_updated_model.root.can_think is True
    assert parsed_updated_model.root.infini_gram_index == AvailableInfiniGramIndexId.OLMO_2_0325_32B
    assert parsed_updated_model.root.temperature_default == new_constraints["temperature_default"]
    assert parsed_updated_model.root.top_p_default == new_constraints["top_p_default"]
    assert parsed_updated_model.root.max_tokens_default == new_constraints["max_tokens_default"]
    assert parsed_updated_model.root.stop_default == new_constraints["stop_default"]


async def test_should_update_a_multi_modal_model(client: AsyncClient, auth_user: AuthenticatedClient):
    model_id = f"test-model-{uuid4()}"

    create_model_request = CreateMultiModalModelConfigRequest(
        id=model_id,
        name="multi-modal model made for testing",
        description="This model is made for testing",
        model_id_on_host="test-mm-model-id",
        model_type=ModelType.Chat,
        host=ModelHost.InferD,
        prompt_type=PromptType.MULTI_MODAL,
        accepted_file_types=["image/*"],
        max_files_per_message=1,
        allow_files_in_followups=False,
    )

    create_response = await client.post(
        ADMIN_MODEL_CONFIG_ENDPOINT,
        json=create_model_request.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    create_response.raise_for_status()

    update_model_request = UpdateMultiModalModelConfigRequest(
        name="multi-modal model made for testing",
        description="updated",
        model_id_on_host="test-mm-model-id",
        model_type=ModelType.Chat,
        host=ModelHost.InferD,
        prompt_type=PromptType.MULTI_MODAL,
        accepted_file_types=["image/*", "application/pdf"],
        max_files_per_message=1,
        allow_files_in_followups=True,
    )

    update_model_response = await client.put(
        f"{ADMIN_MODEL_CONFIG_ENDPOINT}{model_id}",
        json=update_model_request.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    update_model_response.raise_for_status()
    assert update_model_response.status_code == 200

    available_models = await list_admin_models(client, auth_user)

    updated_model = next(filter(lambda model: model.get("id") == model_id, available_models))
    assert updated_model is not None, "Updated model not returned from models endpoint"

    parsed_updated_model = ModelConfigResponse.model_validate(updated_model)
    assert isinstance(parsed_updated_model.root, MultiModalModelConfigResponse)
    assert parsed_updated_model.root.description == "updated"
    assert parsed_updated_model.root.allow_files_in_followups is True
    assert parsed_updated_model.root.accepted_file_types == [
        "image/*",
        "application/pdf",
    ]


async def test_should_error_on_invalid_constraints_update(client: AsyncClient, auth_user: AuthenticatedClient):
    model_id = f"test-model-{uuid4()}"

    model_config_defaults = {
        "name": "model made for testing",
        "description": "This model is made for testing",
        "model_id_on_host": "test-model-id",
        "model_type": ModelType.Chat,
        "host": ModelHost.InferD,
        "prompt_type": PromptType.TEXT_ONLY,
    }

    create_model_request = CreateTextOnlyModelConfigRequest(
        id=model_id,
        **model_config_defaults,
    )

    create_response = await client.post(
        ADMIN_MODEL_CONFIG_ENDPOINT,
        json=create_model_request.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    create_response.raise_for_status()

    created_model = create_response.json()
    assert created_model.get("temperatureDefault") == default_inference_constraints["temperature_default"]
    assert created_model.get("topPDefault") == default_inference_constraints["top_p_default"]
    assert created_model.get("maxTokensDefault") == default_inference_constraints["max_tokens_default"]
    assert created_model.get("stopDefault") == default_inference_constraints["stop_default"]

    max_tokens_override = {"max_tokens_default": cast(int, default_inference_constraints["max_tokens_upper"]) + 10}
    update_model_max_tokens = {**model_config_defaults, **max_tokens_override}

    update_model_too_high = await client.put(
        f"{ADMIN_MODEL_CONFIG_ENDPOINT}{model_id}",
        json=update_model_max_tokens,
        headers=auth_headers_for_user(auth_user),
    )
    assert update_model_too_high.status_code == 422

    temperature_override = {"temperature_default": cast(int, default_inference_constraints["temperature_lower"]) - 10}
    update_model_temperature = {**model_config_defaults, **temperature_override}

    update_model_too_low = await client.put(
        f"{ADMIN_MODEL_CONFIG_ENDPOINT}{model_id}",
        json=update_model_temperature,
        headers=auth_headers_for_user(auth_user),
    )
    assert update_model_too_low.status_code == 422


async def test_should_delete_a_model(client: AsyncClient, auth_user: AuthenticatedClient):
    model_id = f"test-model-{uuid4()}"

    create_model_request = CreateTextOnlyModelConfigRequest(
        id=model_id,
        name="model made for testing",
        description="This model is made for testing",
        model_id_on_host="test-model-id",
        model_type=ModelType.Chat,
        host=ModelHost.InferD,
        prompt_type=PromptType.TEXT_ONLY,
    )

    create_response = await client.post(
        ADMIN_MODEL_CONFIG_ENDPOINT,
        json=create_model_request.model_dump(by_alias=True),
        headers=auth_headers_for_user(auth_user),
    )
    create_response.raise_for_status()

    delete_response = await client.delete(
        f"{ADMIN_MODEL_CONFIG_ENDPOINT}{model_id}", headers=auth_headers_for_user(auth_user)
    )
    delete_response.raise_for_status()
    assert delete_response.status_code == 204

    available_models = await list_admin_models(client, auth_user)

    assert all(model["id"] != model_id for model in available_models), "Model wasn't deleted"


async def test_should_reorder_models(client: AsyncClient, auth_user: AuthenticatedClient):
    # Create models to arrange
    model_ids = ["model-a", "model-b", "model-c"]
    for model_id in model_ids:
        create_model_request = CreateTextOnlyModelConfigRequest(
            id=model_id,
            name=f"{model_id} name",
            description=f"{model_id} desc",
            model_id_on_host=f"{model_id}-host",
            model_type=ModelType.Chat,
            host=ModelHost.InferD,
            prompt_type=PromptType.TEXT_ONLY,
        )

        create_response = await client.post(
            ADMIN_MODEL_CONFIG_ENDPOINT,
            json=create_model_request.model_dump(by_alias=True),
            headers=auth_headers_for_user(auth_user),
        )
        create_response.raise_for_status()

    # reordered data
    reordered = [
        {"id": "model-c", "order": 1},
        {"id": "model-b", "order": 2},
        {"id": "model-a", "order": 3},
    ]

    reorder_response = await client.put(
        ADMIN_MODEL_CONFIG_ENDPOINT, json={"ordered_models": reordered}, headers=auth_headers_for_user(auth_user)
    )
    reorder_response.raise_for_status()

    models = await list_admin_models(client, auth_user)

    test_models = sorted(
        [m for m in models if m["id"] in model_ids],
        key=operator.itemgetter("order"),
    )

    expected_order = ["model-c", "model-b", "model-a"]
    actual_order = [m["id"] for m in test_models]
    assert actual_order == expected_order, f"Expected order {expected_order}, got {actual_order}"
