import dataclasses
import requests

from src.inference.inference_service import ModelEntity

from . import base


class TestModelEndpoints(base.IntegrationTest):
    client: base.AuthenticatedClient

    def runTest(self):
        self.shouldFailWithoutAuth()

        self.client = self.user("test@localhost")
        self.shouldGetAListOfModelEntities()

    def shouldFailWithoutAuth(self):
        r = requests.get(f"{self.origin}/v3/models")
        assert r.status_code == 401

    def shouldGetAListOfModelEntities(self):
        r = requests.get(f"{self.origin}/v3/models", headers=self.auth(self.client))
        r.raise_for_status()

        response = r.json()

        # should have at least one model entity
        assert len(response) > 0

        # should have the following fields that match ModelEntity
        entity = response.pop()
        for field in dataclasses.fields(ModelEntity):
            assert field.name in entity
