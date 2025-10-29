from sqlalchemy.orm import Session

from src.auth.token import Token
from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelConfig, ModelHost, ModelType, PromptType
from src.dao.message.message_models import InferenceOpts, Role
from src.dao.message.message_repository import MessageRepository
from src.message.create_message_request import (
    CreateMessageRequestWithFullMessages,
)
from src.message.create_message_service.database import create_user_message, setup_msg_thread


class TestDatabase:
    def test_thread_setup(self, sql_alchemy: Session):
        message_repo = MessageRepository(sql_alchemy)
        request = CreateMessageRequestWithFullMessages(
            captcha_token="",
            parent_id=None,
            parent=None,
            opts=InferenceOpts(),
            content="Hello world",
            role=Role.User,
            model="123",
            client="xyz",
            create_tool_definitions=None,
            selected_tools=None,
            enable_tool_calling=False,
            agent=None,
            mcp_server_ids=None,
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
            temperature_default=0.7,
            temperature_upper=1.0,
            temperature_lower=0.0,
            temperature_step=0.01,
            top_p_default=1.0,
            top_p_upper=1.0,
            top_p_lower=0.0,
            top_p_step=0.01,
            max_tokens_default=2048,
            max_tokens_upper=2048,
            max_tokens_lower=1,
            max_tokens_step=1,
            stop_default=None,
        )

        token = Token(client="1234", is_anonymous_user=False, token="hello")

        thread_setup = setup_msg_thread(
            message_repository=message_repo, model=model, request=request, creator_token=token, agent_id=None
        )

        assert len(thread_setup) == 1
        assert thread_setup[0].role == Role.System

        result = sql_alchemy.query(Message).all()
        assert len(result) == 1
        assert result[0].id == thread_setup[0].id

    def test_thread_setup_two(self, sql_alchemy: Session):
        message_repo = MessageRepository(sql_alchemy)
        request = CreateMessageRequestWithFullMessages(
            captcha_token="",
            parent_id=None,
            parent=None,
            opts=InferenceOpts(),
            content="Hello world",
            role=Role.User,
            model="123",
            client="xyz",
            create_tool_definitions=None,
            selected_tools=None,
            enable_tool_calling=False,
            agent=None,
            mcp_server_ids=None,
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
            temperature_default=0.7,
            temperature_upper=1.0,
            temperature_lower=0.0,
            temperature_step=0.01,
            top_p_default=1.0,
            top_p_upper=1.0,
            top_p_lower=0.0,
            top_p_step=0.01,
            max_tokens_default=2048,
            max_tokens_upper=2048,
            max_tokens_lower=1,
            max_tokens_step=1,
            stop_default=None,
        )

        token = Token(client="1234", is_anonymous_user=False, token="hello")

        user_message = create_user_message(
            message_repository=message_repo,
            parent=None,
            model=model,
            request=request,
            creator_token=token,
            agent_id=None,
            include_mcp_servers=None,
        )

        result = sql_alchemy.query(Message).all()
        assert len(result) == 1
        assert result[0].id == user_message.id
