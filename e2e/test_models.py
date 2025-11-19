import json
import operator
from uuid import uuid4

import requests

from src.attribution.infini_gram_api_client.models.available_infini_gram_index_id import AvailableInfiniGramIndexId
from src.dao.engine_models.model_config import ModelHost, ModelType, PromptType
from src.model_config.create_model_config_service import (
    BaseCreateModelConfigRequest,
    CreateMultiModalModelConfigRequest,
    CreateTextOnlyModelConfigRequest,
)
from src.model_config.get_model_config_service import AdminModelResponse, ModelResponse
from src.model_config.response_model import MultiModalResponseModel, ResponseModel
from src.model_config.update_model_config_service import (
    UpdateMultiModalModelConfigRequest,
    UpdateTextOnlyModelConfigRequest,
)

from . import base

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


class BaseTestV4ModelEndpoints(base.IntegrationTest):
    client: base.AuthenticatedClient
    created_model_ids: list[str]

    @property
    def model_endpoint(self):
        return f"{self.origin}/v4/models"

    @property
    def model_config_endpoint(self):
        return f"{self.origin}/v4/admin/models"

    def setUp(self):
        self.created_model_ids = []

    def create_model(self, request: BaseCreateModelConfigRequest, *, skip_cleanup=False):
        response = requests.post(
            self.model_config_endpoint,
            json=request.model_dump(by_alias=True),
            headers=self.auth(self.client),
        )

        if not skip_cleanup:
            self.created_model_ids.append(request.id)

        return response

    def list_admin_models(self):
        r = requests.get(
            self.model_config_endpoint,
            headers=self.auth(self.client),
        )
        r.raise_for_status()

        return r.json()

    def list_models(self):
        r = requests.get(self.model_endpoint, headers=self.auth(self.client))
        r.raise_for_status()

        return r.json()

    def tearDown(self):
        for model_id in self.created_model_ids:
            delete_response = requests.delete(
                self.model_config_endpoint + "/" + model_id,
                headers=self.auth(self.client),
            )
            assert delete_response.status_code == 204


class TestV4ModelEndpoints(BaseTestV4ModelEndpoints):
    client: base.AuthenticatedClient
    created_model_ids: list[str]

    def setUp(self):
        self.client = self.user()
        self.created_model_ids = []

    def test_get_a_list_of_models(self):
        response = self.list_models()

        # should have at least one model entity
        assert len(response) > 0

        # should have the following fields that match ModelEntity
        entity = response.pop()
        assert "is_visible" in entity
        assert "host" in entity
        assert "compute_source_id" not in entity
        assert "available_time" not in entity
        assert "deprecation_time" not in entity

    def test_get_admin_models(self):
        response = self.list_admin_models()

        if isinstance(response, list):
            # should have at least one model entity
            assert len(response) > 0

            # should have the following fields that match ModelEntity
            entity = response[0]
            assert "is_visible" not in entity
            assert "host" in entity
            assert "modelIdOnHost" in entity
            assert "availableTime" in entity
            assert "deprecationTime" in entity
        else:
            msg = "Response returned from GET /v4/models was not a list"
            raise TypeError(msg)

    def test_should_create_a_model(self):
        model_id = "test-model-" + str(uuid4())
        create_model_request = CreateTextOnlyModelConfigRequest(
            id=model_id,
            name="model made for testing",
            description="This model is made for testing",
            model_id_on_host="test-model-id",
            model_type=ModelType.Chat,
            host=ModelHost.InferD,
            prompt_type=PromptType.TEXT_ONLY,
            can_think=True,
        )

        create_response = self.create_model(create_model_request)
        create_response.raise_for_status()

        created_model = create_response.json()
        assert created_model.get("createdTime") is not None
        assert created_model.get("modelType") == "chat"
        assert created_model.get("canThink") is True
        assert created_model.get("temperatureDefault") == default_inference_constraints["temperature_default"]
        assert created_model.get("topPDefault") == default_inference_constraints["top_p_default"]
        assert created_model.get("maxTokensDefault") == default_inference_constraints["max_tokens_default"]
        assert created_model.get("stopDefault") == default_inference_constraints["stop_default"]

        available_models = self.list_admin_models()

        test_model = next((model for model in available_models if model.get("id") == model_id), None)
        assert test_model is not None, "The test model wasn't returned from the GET request"

    def test_should_create_a_multi_modal_model(self):
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

        create_response = self.create_model(create_model_request)
        create_response.raise_for_status()

        created_model = create_response.json()
        assert created_model.get("createdTime") is not None
        assert created_model.get("modelType") == "chat"

        available_models = self.list_models()
        test_model = next((model for model in available_models if model.get("id") == model_id), None)

        assert test_model is not None, "The test model wasn't returned from the GET request"
        assert "image/*" in test_model.get("accepted_file_types")
        assert test_model.get("accepts_files") is True

    def test_should_create_a_model_with_tool_calling_enabled(self):
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

        create_response = self.create_model(create_model_request)
        create_response.raise_for_status()

        created_model = ResponseModel.model_validate(create_response.json())
        assert created_model.root.created_time is not None
        assert created_model.root.model_type == "chat"
        assert created_model.root.can_call_tools is True

        available_models = AdminModelResponse.model_validate(self.list_admin_models())

        test_admin_model = next((model for model in available_models.root if model.root.id == model_id), None)
        assert test_admin_model is not None, "The test model wasn't returned from the GET request"
        assert test_admin_model.root.can_call_tools is True

        # Make sure tool call mapping worked. This may be able to be combined with the admin tool once we set up the available tool config on admin models
        models = ModelResponse.model_validate(self.list_models())
        test_model = next((model for model in models.root if model.id == model_id), None)
        assert test_model is not None, "The test model wasn't returned from the GET request"
        assert test_model.can_call_tools is True
        assert test_model.available_tools is not None, "Available tools weren't set on a tool-calling model"
        assert len(test_model.available_tools) > 0

    def test_should_create_a_model_with_an_infini_gram_index(self):
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

        create_response = self.create_model(create_model_request)
        create_response.raise_for_status()

        created_model = ResponseModel.model_validate(create_response.json()).root
        assert created_model.created_time is not None
        assert created_model.model_type == "chat"
        assert created_model.infini_gram_index == AvailableInfiniGramIndexId.OLMO_2_0325_32B

        available_models = self.list_admin_models()

        test_model = ResponseModel.model_validate(
            next((model for model in available_models if model.get("id") == model_id), None)
        ).root
        assert test_model is not None, "The test model wasn't returned from the GET request"
        assert created_model.infini_gram_index == AvailableInfiniGramIndexId.OLMO_2_0325_32B

    def test_should_delete_a_model(self):
        model_id = "test-model-" + str(uuid4())

        create_model_request = CreateTextOnlyModelConfigRequest(
            id=model_id,
            name="model made for testing",
            description="This model is made for testing",
            model_id_on_host="test-model-id",
            model_type=ModelType.Chat,
            host=ModelHost.InferD,
            prompt_type=PromptType.TEXT_ONLY,
        )

        create_response = self.create_model(create_model_request, skip_cleanup=True)
        create_response.raise_for_status()

        delete_response = requests.delete(
            self.model_config_endpoint + "/" + model_id,
            headers=self.auth(self.client),
        )
        delete_response.raise_for_status()
        assert delete_response.status_code == 204

        available_models = self.list_admin_models()

        assert all(model["id"] != model_id for model in available_models), "Model wasn't deleted"

    def test_should_reorder_models(self):
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

            create_response = self.create_model(create_model_request)
            create_response.raise_for_status()

        reordered = [
            {"id": "model-c", "order": 1},
            {"id": "model-b", "order": 2},
            {"id": "model-a", "order": 3},
        ]

        reorder_response = requests.put(
            self.model_config_endpoint,
            json={"ordered_models": reordered},
            headers=self.auth(self.client),
        )
        reorder_response.raise_for_status()

        models = self.list_admin_models()

        test_models = sorted([m for m in models if m["id"] in model_ids], key=operator.itemgetter("order"))

        expected_order = ["model-c", "model-b", "model-a"]
        actual_order = [m["id"] for m in test_models]
        assert actual_order == expected_order, f"Expected order {expected_order}, got {actual_order}"

    def test_should_update_a_text_only_model(self):
        model_id = "test-model-" + str(uuid4())

        create_model_request = CreateTextOnlyModelConfigRequest(
            id=model_id,
            name="model made for testing",
            description="This model is made for testing",
            model_id_on_host="test-model-id",
            model_type=ModelType.Chat,
            host=ModelHost.InferD,
            prompt_type=PromptType.TEXT_ONLY,
        )

        create_response = self.create_model(create_model_request)
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
        update_model_response = requests.put(
            self.model_config_endpoint + "/" + model_id,
            headers=self.auth(self.client),
            json=update_model_request.model_dump(by_alias=True),
        )
        update_model_response.raise_for_status()
        assert update_model_response.status_code == 200

        available_models = self.list_admin_models()

        updated_model = ResponseModel(next(filter(lambda model: model.get("id") == model_id, available_models))).root
        assert updated_model is not None, "Updated model not returned from models endpoint"
        assert updated_model.name == "updated model made for testing"
        assert updated_model.model_type == "base"
        assert updated_model.can_call_tools is True
        assert updated_model.can_think is True
        assert updated_model.infini_gram_index == AvailableInfiniGramIndexId.OLMO_2_0325_32B
        assert updated_model.temperature_default == new_constraints["temperature_default"]
        assert updated_model.top_p_default == new_constraints["top_p_default"]
        assert updated_model.max_tokens_default == new_constraints["max_tokens_default"]
        assert updated_model.stop_default == new_constraints["stop_default"]

    def test_should_update_a_multi_modal_model(self):
        model_id = "test-model-" + str(uuid4())

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

        create_response = self.create_model(create_model_request)
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

        update_model_response = requests.put(
            self.model_config_endpoint + "/" + model_id,
            headers=self.auth(self.client),
            json=update_model_request.model_dump(by_alias=True),
        )
        update_model_response.raise_for_status()
        assert update_model_response.status_code == 200

        available_models = self.list_admin_models()

        updated_model = next(filter(lambda model: model.get("id") == model_id, available_models))
        assert updated_model is not None, "Updated model not returned from models endpoint"

        parsed_updated_model = ResponseModel.model_validate(updated_model)
        assert isinstance(parsed_updated_model.root, MultiModalResponseModel)
        assert parsed_updated_model.root.description == "updated"
        assert parsed_updated_model.root.allow_files_in_followups is True
        assert parsed_updated_model.root.accepted_file_types == [
            "image/*",
            "application/pdf",
        ]

    def test_should_error_on_invalid_constraints_update(self):
        model_id = "test-model-" + str(uuid4())
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

        create_response = self.create_model(create_model_request)
        create_response.raise_for_status()

        created_model = create_response.json()
        assert created_model.get("temperatureDefault") == default_inference_constraints["temperature_default"]
        assert created_model.get("topPDefault") == default_inference_constraints["top_p_default"]
        assert created_model.get("maxTokensDefault") == default_inference_constraints["max_tokens_default"]
        assert created_model.get("stopDefault") == default_inference_constraints["stop_default"]

        max_tokens_override = {"max_tokens_default": default_inference_constraints["max_tokens_upper"] + 10}
        update_model_max_tokens = {**model_config_defaults, **max_tokens_override}
        update_model_response1 = requests.put(
            self.model_config_endpoint + "/" + model_id,
            headers=self.auth(self.client),
            json=json.dumps(update_model_max_tokens),
        )
        assert update_model_response1.status_code == 400

        temperature_override = {"temperature_default": default_inference_constraints["temperature_lower"] - 10}
        update_model_temperature = {**model_config_defaults, **temperature_override}
        update_model_response2 = requests.put(
            self.model_config_endpoint + "/" + model_id,
            headers=self.auth(self.client),
            json=json.dumps(update_model_temperature),
        )
        assert update_model_response2.status_code == 400


class TestV4ModelEndpointsAnonymous(BaseTestV4ModelEndpoints):
    def setUp(self):
        super().setUp()
        self.client = self.user(anonymous=True)

    def test_get_public_models(self):
        r = requests.get(
            f"{self.origin}/v4/models",
            headers=self.auth(self.client),
        )
        r.raise_for_status()
        response = r.json()

        # should have at least one model entity
        self.assertGreater(len(response), 0)
        self.assertEqual(len([model for model in response if model.get("internal") is True]), 0)

    def test_get_admin_models_should_be_forbidden(self):
        r = requests.get(
            f"{self.origin}/v4/admin/models",
            headers=self.auth(self.client),
        )

        self.assertEqual(r.status_code, 401)
