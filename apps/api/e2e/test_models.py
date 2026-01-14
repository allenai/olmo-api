from uuid import uuid4

import pytest
from httpx import AsyncClient

from api.model_config.admin.model_config_admin_create_service import (
    CreateMultiModalModelConfigRequest,
    CreateTextOnlyModelConfigRequest,
)
from api.model_config.model_config_response import (
    AvailableInfiniGramIndexId,
    ModelConfigListResponse,
    ModelConfigResponse,
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


async def test_create_text_only_model(
    client: AsyncClient,
    auth_user: AuthenticatedClient,
):
    model_id = "test-model-" + str(uuid4())
    create_model_request = CreateTextOnlyModelConfigRequest(
        id=model_id,
        name="model made for testing",
        description="This model is made for testing",
        model_id_on_host="test-model-id",
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
    model_id = "test-mm-model-" + str(uuid4())
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
    model_id = "test-tool-model-" + str(uuid4())
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
    model_id = "test-tool-model-" + str(uuid4())
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


# TODO: Implement skipped tests from from flask-api
#
@pytest.mark.skip(reason="Public endpoint not yet implemented")
async def test_get_a_list_of_models():
    pass


@pytest.mark.skip(reason="Test not yet implemented")
async def test_get_admin_models():
    pass


@pytest.mark.skip(reason="DELETE endpoint not yet implemented")
async def test_should_delete_a_model():
    pass


@pytest.mark.skip(reason="Reorder endpoint not yet implemented")
async def test_should_reorder_models():
    pass


@pytest.mark.skip(reason="UPDATE endpoint not yet implemented")
async def test_should_update_a_text_only_model():
    pass


@pytest.mark.skip(reason="UPDATE endpoint not yet implemented")
async def test_should_update_a_multi_modal_model():
    pass


@pytest.mark.skip(reason="UPDATE endpoint not yet implemented")
async def test_should_error_on_invalid_constraints_update():
    pass


@pytest.mark.skip(reason="Public endpoint not yet implemented")
async def test_get_public_models():
    pass


@pytest.mark.skip(reason="Anonymous auth not yet configured")
async def test_get_admin_models_should_be_forbidden():
    pass
