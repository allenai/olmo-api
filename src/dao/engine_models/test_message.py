import pytest
from sqlalchemy.orm import Session

from src.auth.token import Token
from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelConfig, ModelHost, ModelType, PromptType
from src.dao.message.message_models import InferenceOpts, Role
from src.dao.message.message_repository import MessageRepository
from src.message.create_message_request import (
    CreateMessageRequestWithFullMessages,
)
import dataclasses
from src.message.create_message_service.database import create_user_message, setup_msg_thread


@pytest.mark.integration
class TestDatabase:
    def test_convert_database_message_to_json(self, sql_alchemy: Session):
        message_repo = MessageRepository(sql_alchemy)
        message = Message(
            content="Hello world",
            role=Role.User,
            opts={},
            model_id="123",
            model_host="parent.model_host",
            model_type=ModelType.Chat,
            root="",
            parent="parent.id",
            template=None,
            final=True,
            original=None,
            private=False,
            harmful=False,
            expiration_time=None,
            creator="",
        )

        message_repo.add(message)

        dictionary = dataclasses.asdict(message)
