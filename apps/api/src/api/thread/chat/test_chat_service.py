import pytest
from pytest_mock import MockerFixture

from api.thread.chat.chat_request import CreateToolDefinition, ParameterDef
from api.thread.chat.chat_service import ChatService
from db.models.model_config import ModelConfig, ModelHost, ModelType, PromptType


def create_fake_model(*, can_call_tools: bool):
    return ModelConfig(
        id="fake-model",
        can_call_tools=can_call_tools,
        host=ModelHost.TestBackend,
        name="Fake model",
        description="Fake model",
        model_type=ModelType.Chat,
        model_id_on_host="fake-model",
        internal=False,
        prompt_type=PromptType.TEXT_ONLY,
        temperature_default=0,
        temperature_upper=0,
        temperature_lower=0,
        temperature_step=0,
        top_p_default=0,
        top_p_lower=0,
        top_p_upper=0,
        top_p_step=1,
        max_tokens_default=1,
        max_tokens_lower=1,
        max_tokens_upper=1,
        max_tokens_step=1,
    )


@pytest.fixture(autouse=True)
def mock_get_mcp_servers(mocker: MockerFixture):
    mocker.patch("api.thread.chat.chat_service.get_general_mcp_servers", return_value=[])


def test_get_toolsets_returns_empty_if_model_cannot_call_tools():

    toolsets = ChatService._get_toolsets(  # noqa: SLF001
        create_fake_model(can_call_tools=False),
        user_tools=[
            CreateToolDefinition(name="Tool", description="This sure is a tool", parameters=ParameterDef(type="object"))
        ],
        mcp_tools=["fake_tool"],
    )

    assert len(toolsets) == 0


async def test_get_toolsets_returns_user_and_mcp_tools():
    toolsets = ChatService._get_toolsets(  # noqa: SLF001
        create_fake_model(can_call_tools=True),
        user_tools=[
            CreateToolDefinition(name="Tool", description="This sure is a tool", parameters=ParameterDef(type="object"))
        ],
        mcp_tools=["fake_tool"],
    )

    assert len(toolsets) == 2
    assert len(await toolsets[0].get_tools(None)) == 1  # pyright: ignore[reportArgumentType]
    # This mostly tests to make sure our mcp server mock is working. If it starts failing make sure to fix the mock!
    assert len(await toolsets[1].get_tools(None)) == 0  # pyright: ignore[reportArgumentType]
