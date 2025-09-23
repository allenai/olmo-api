import dataclasses

import json
import pytest
from sqlalchemy.orm import Session

from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelType
from src.dao.message.message_models import Role
from src.dao.message.message_repository import MessageRepository

from src import db, util


@pytest.mark.integration
class TestDatabase:
    def test_convert_database_message_to_json(self, sql_alchemy: Session):
        message_repo = MessageRepository(sql_alchemy)
        id = "123124"
        message = Message(
            id=id,
            content="Hello world",
            role=Role.User,
            opts={},
            model_id="123",
            model_host="parent.model_host",
            model_type=ModelType.Chat,
            root=id,
            parent=None,
            template=None,
            final=True,
            original=None,
            private=False,
            harmful=False,
            expiration_time=None,
            creator="",
        )

        message_repo.add(message)

        messageTwo = Message(
            content="Hello world",
            role=Role.Assistant,
            opts={},
            model_id="123",
            model_host="parent.model_host",
            model_type=ModelType.Chat,
            root=id,
            parent=id,
            template=None,
            final=True,
            original=None,
            private=False,
            harmful=False,
            expiration_time=None,
            creator="",
        )

        dictionary = dataclasses.asdict(messageTwo)

        json_obj = json.dumps(obj=dictionary, cls=util.CustomEncoder) + "\n"
