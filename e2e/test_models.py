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
        assert "compute_source_id" not in entity
        assert "available_time" not in entity
        assert "deprecation_time" not in entity
