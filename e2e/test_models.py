import requests

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

        # should have at least one model entity
        assert len(response) > 0

        # should have the following fields that match ModelEntity
        entity = response.pop()
        assert "is_visible" in entity
        assert "host" in entity
        assert "compute_source_id" not in entity
        assert "available_time" not in entity
        assert "deprecation_time" not in entity


class TestV4ModelEndpoints(base.IntegrationTest):
    client: base.AuthenticatedClient

    def runTest(self):
        self.client = self.user()
        self.shouldAddAModel()
        self.shouldDeleteModel()

    def shouldAddAModel(self):
        model_id = "test-model"
        create_model_request = {
            "id": model_id,
            "name": "model made for testing",
            "description": "This model is made for testing",
            "modelIdOnHost": "test-model-id",
            "modelType": "chat",
            "host": "inferd",
            "promptType": "text_only",
        }
        create_response = requests.post(
            f"{self.origin}/v4/models/",
            json=create_model_request,
            headers=self.auth(self.client),
        )
        create_response.raise_for_status()

        created_model = create_response.json()

        assert created_model.get("createdTime") is not None
        assert created_model.get("modelType") == "chat"

        get_models_response = requests.get(
            f"{self.origin}/v4/models/", headers=self.auth(self.client)
        )
        get_models_response.raise_for_status()

        available_models = get_models_response.json()

        test_model = next(
            (model for model in available_models if model.get("id") == model_id), None
        )
        assert (
            test_model is not None
        ), "The test model wasn't returned from the GET request"

        # TODO: clean up created models

    def shouldDeleteModel(self):
        model_id = "test-model-2"
        create_model_request = {
            "id": model_id,
            "name": "model made for testing",
            "description": "This model is made for testing",
            "modelIdOnHost": "test-model-id",
            "modelType": "chat",
            "host": "inferd",
            "promptType": "text_only",
        }
        create_response = requests.post(
            f"{self.origin}/v4/models/",
            json=create_model_request,
            headers=self.auth(self.client),
        )
        create_response.raise_for_status()

        delete_response = requests.delete(
            f"{self.origin}/v4/models/{model_id}",
            headers=self.auth(self.client),
        )

        delete_response.raise_for_status()
        assert delete_response.status_code == 204

        get_models_response = requests.get(
            f"{self.origin}/v4/models/", headers=self.auth(self.client)
        )
        get_models_response.raise_for_status()
        available_models = get_models_response.json()

        assert all(
            model["id"] != model_id for model in available_models
        ), "Model wasn't deleted"
