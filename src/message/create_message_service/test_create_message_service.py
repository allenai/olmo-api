from sqlalchemy.orm import Session

from src.auth.token import Token
from src.dao.engine_models.model_config import ModelConfig, ModelHost, ModelType, PromptType
from src.dao.message.message_models import InferenceOpts, Role
from src.dao.message.message_repository import MessageRepository
from src.message.create_message_request import (
    CreateMessageRequestWithFullMessages,
)
from src.message.create_message_service.database import setup_msg_thread


def test_thread_setup(sql_alchemy: Session):
    message_repo = MessageRepository(sql_alchemy)
    request = CreateMessageRequestWithFullMessages(
        captcha_token="",
        parent_id=None,
        parent=None,
        opts=InferenceOpts(),
        content="Hello world",
        role=Role.User,
        model="123",
        host="123",
        client="xyz",
    )

    model = ModelConfig(
        id="123",
        host=ModelHost.TestBackend,
        name="",
        description="",
        model_type=ModelType.Chat,
        model_id_on_host="",
        internal=True,
        prompt_type=PromptType.TEXT_ONLY,
        default_system_prompt="You are an Ai! Go take over the world!",
    )

    token = Token(client="1234", is_anonymous_user=False, token="hello")

    thread_setup = setup_msg_thread(message_repository=message_repo, model=model, request=request, agent=token)

    assert len(thread_setup) == 1
    assert thread_setup[0].role == Role.System
