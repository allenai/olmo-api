from uuid import uuid4

import requests

from src.dao.engine_models.model_config import ModelHost, ModelType, PromptType
from src.model_config.create_model_config_service import (
    BaseCreateModelConfigRequest,
    CreateMultiModalModelConfigRequest,
    CreateTextOnlyModelConfigRequest,
)
from src.model_config.response_model import MultiModalResponseModel, ResponseModel
from src.model_config.update_model_config_service import (
    UpdateMultiModalModelConfigRequest,
    UpdateTextOnlyModelConfigRequest,
)

from . import base


class TestModelEndpoints(base.IntegrationTest):
    client: base.AuthenticatedClient

    def runTest(self):
        self.client = self.user(anonymous=True)
        self.shouldGetAListOfModels()

    def shouldGetAListOfModels(self):
        r = requests.get(f"{self.origin}/v3/models", headers=self.auth(self.client))
        r.raise_for_status()

        response = r.json()
        assert len(response) > 0

        entity = response.pop()
        assert "is_visible" in entity
        assert "host" in entity
        assert "compute_source_id" not in entity
        assert "available_time" not in entity


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
        r = requests.get(self.model_endpoint, headers=self.auth(self.client))
        r.raise_for_status()

        response = r.json()

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
        r = requests.get(
            self.model_config_endpoint,
            headers=self.auth(self.client),
        )
        r.raise_for_status()

        response = r.json()

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
        )

        create_response = self.create_model(create_model_request)
        create_response.raise_for_status()

        created_model = create_response.json()
        assert created_model.get("createdTime") is not None
        assert created_model.get("modelType") == "chat"

        get_models_response = requests.get(self.model_config_endpoint, headers=self.auth(self.client))
        get_models_response.raise_for_status()

        available_models = get_models_response.json()

        test_model = next((model for model in available_models if model.get("id") == model_id), None)
        assert test_model is not None, "The test model wasn't returned from the GET request"

    def test_should_create_a_multi_modal_model(self):
        model_id = "test-mm-model"
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

        get_models_response = requests.get(f"{self.origin}/v4/models/", headers=self.auth(self.client))
        get_models_response.raise_for_status()

        available_models = get_models_response.json()
        test_model = next((model for model in available_models if model.get("id") == model_id), None)
        assert test_model is not None, "The test model wasn't returned from the GET request"
        assert "image/*" in test_model.get("accepted_file_types")
        assert test_model.get("accepts_files") is True

    def test_should_create_a_model_with_tool_calling_enabled(self):
        model_id = "test-tool-model"
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

        created_model = create_response.json()
        assert created_model.get("createdTime") is not None
        assert created_model.get("modelType") == "chat"
        assert created_model.get("canCallTools") is True

        get_models_response = requests.get(self.model_config_endpoint, headers=self.auth(self.client))
        get_models_response.raise_for_status()

        available_models = get_models_response.json()

        test_model = next((model for model in available_models if model.get("id") == model_id), None)
        assert test_model is not None, "The test model wasn't returned from the GET request"
        assert test_model.get("canCallTools") is True

    def test_should_delete_a_model(self):
        model_id = "test-model"
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

        get_models_response = requests.get(self.model_config_endpoint, headers=self.auth(self.client))
        get_models_response.raise_for_status()
        available_models = get_models_response.json()

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

        get_response = requests.get(
            self.model_config_endpoint,
            headers=self.auth(self.client),
        )
        get_response.raise_for_status()
        models = get_response.json()

        test_models = sorted([m for m in models if m["id"] in model_ids], key=lambda m: m["order"])

        expected_order = ["model-c", "model-b", "model-a"]
        actual_order = [m["id"] for m in test_models]
        assert actual_order == expected_order, f"Expected order {expected_order}, got {actual_order}"

    def test_should_update_a_text_only_model(self):
        model_id = "test-model"
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

        update_model_request = UpdateTextOnlyModelConfigRequest(
            name="updated model made for testing",
            description="This model is made for testing",
            model_id_on_host="test-model-id",
            model_type=ModelType.Base,
            host=ModelHost.Modal,
            prompt_type=PromptType.TEXT_ONLY,
            can_call_tools=True,
        )
        update_model_response = requests.put(
            self.model_config_endpoint + "/" + model_id,
            headers=self.auth(self.client),
            json=update_model_request.model_dump(by_alias=True),
        )
        update_model_response.raise_for_status()
        assert update_model_response.status_code == 200

        get_models_response = requests.get(
            self.model_config_endpoint,
            headers=self.auth(self.client),
        )
        get_models_response.raise_for_status()
        available_models = get_models_response.json()

        updated_model = next(filter(lambda model: model.get("id") == model_id, available_models))
        assert updated_model is not None, "Updated model not returned from models endpoint"
        assert updated_model.get("name") == "updated model made for testing"
        assert updated_model.get("modelType") == "base"
        assert updated_model.get("canCallTools") is True

    def test_should_update_a_multi_modal_model(self):
        model_id = "test-model"
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

        get_models_response = requests.get(
            self.model_config_endpoint,
            headers=self.auth(self.client),
        )
        get_models_response.raise_for_status()
        available_models = get_models_response.json()

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
