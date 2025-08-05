from unittest.mock import Mock

import pytest
from flask import current_app

from app import create_app
from src.auth.token import Token
from src.dao import message
from src.dao.engine_models.model_config import ModelConfig, ModelHost, ModelType, PromptType
from src.db import Client
from src.message.create_message_request import (
    CreateMessageRequestWithFullMessages,
)
from src.message.create_message_service import safety
from src.message.GoogleCloudStorage import GoogleCloudStorage

from .stream_new_message import stream_new_message


def mock_authn():
    return Token(client="123", is_anonymous_user=True, token="1234", created=None)


def mock_safety():
    return True


@pytest.fixture(scope="session")
def app():
    """Create app for the entire test session."""
    app = create_app()

    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


def test_stream_new_message(monkeypatch, client):
    monkeypatch.setattr("src.message.create_message_service.stream_new_message.authn", mock_authn)
    monkeypatch.setattr(safety, "check_message_safety", mock_safety)

    # Create placeholder request object
    request = CreateMessageRequestWithFullMessages(
        parent_id=None,
        parent=None,
        opts=message.InferenceOpts(
            max_tokens=512,
            temperature=0.7,
            n=1,
            top_p=1.0,
            logprobs=None,
            stop=None,
        ),
        content="Test message content",
        role=message.Role.User,
        original=None,
        private=False,
        root=None,
        template=None,
        model="test-model",
        host="inferd",
        client="test-client",
        files=None,
        captcha_token=None,
    )

    # Create mock database client
    mock_dbc = Mock(spec=Client)

    # Create mock storage client
    mock_storage_client = Mock(spec=GoogleCloudStorage)

    # Create model config with placeholder values
    model = ModelConfig(
        id="test-model-id",
        host=ModelHost.PydanticAiTest,
        name="Test Model",
        description="Test model description",
        model_type=ModelType.Chat,
        model_id_on_host="test-model-host-id",
        internal=False,
        prompt_type=PromptType.TEXT_ONLY,
        can_call_tools=False,
    )

    # Call the function with placeholder arguments
    result = stream_new_message(
        request=request,
        dbc=mock_dbc,
        storage_client=mock_storage_client,
        model=model,
    )

    current_app.logger.error("hello")

    if isinstance(result, message.Message):
        return

    for chunk in result:
        if isinstance(chunk, message.Message):
            print(chunk)
