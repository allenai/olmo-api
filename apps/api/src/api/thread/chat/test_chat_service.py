from pydantic_ai import FunctionToolset

from api.test_utils.fake_run_context import make_fake_run_context
from api.thread.chat.chat_request import CreateToolDefinition, ParameterDef
from api.thread.chat.chat_service import ChatService
from core.tools.tool_source import ToolSource
from db.models.model_config import ModelConfig, ModelHost, ModelType, PromptType
from db.models.tool_definitions import ToolDefinition

test_toolset = FunctionToolset()


@test_toolset.tool()
async def celsius_to_fahrenheit(celsius: float) -> float:  # noqa: RUF029
    """Convert Celsius to Fahrenheit.

    Args:
        celsius: Temperature in Celsius

    Returns:
        Temperature in Fahrenheit
    """
    return (celsius * 9 / 5) + 32


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


def get_fake_mcp_service():
    mock_tool = ToolDefinition(
        name="mock_tool",
        tool_source=ToolSource.MCP,
        mcp_server_id="mock-server",
        description="A mock tool for testing",
        parameters={"type": "object", "properties": {}},
    )

    class _MockMcpService:
        @classmethod
        async def get_general_mcp_tools(cls):
            return [mock_tool]

        @classmethod
        async def get_tools_from_mcp_servers(cls, _mcp_server_ids: set[str]):
            return [mock_tool]

        @classmethod
        def get_pydantic_ai_mcp_servers(cls):
            return [test_toolset]

    return _MockMcpService()


async def test_get_toolsets_returns_user_and_mcp_tools():
    chat_service = ChatService(
        mcp_service=get_fake_mcp_service(),  # type:ignore
        message_repository=None,  # type: ignore
        tools_service=None,  # type: ignore
        session=None,  # type: ignore
        file_upload_service=None,  # type: ignore
        validate_message_safety_service=None,  # type: ignore
        request_client=None,  # type: ignore
        auth_user=None,  # type:ignore
    )
    toolsets = chat_service._get_toolsets(  # noqa: SLF001
        user_tools=[
            CreateToolDefinition(name="Tool", description="This sure is a tool", parameters=ParameterDef(type="object"))
        ],
        mcp_tools=["celsius_to_fahrenheit"],
    )

    run_context = make_fake_run_context()

    assert len(toolsets) == 2
    user_toolset_tools = await toolsets[0].get_tools(run_context)
    assert len(user_toolset_tools) == 1
    assert user_toolset_tools.get("Tool") is not None
    # This mostly tests to make sure our mcp server mock is working. If it starts failing make sure to fix the mock!
    assert len(await toolsets[1].get_tools(run_context)) == 1
