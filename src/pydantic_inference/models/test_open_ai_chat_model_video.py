from unittest.mock import AsyncMock, MagicMock

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage
from pydantic_ai.direct import model_request_sync
from pydantic_ai.providers.openai import OpenAIProvider

from src.pydantic_inference.models.open_ai_chat_model_video import OpenAIChatModelVideo

# Models hosted on vLLM always have this name
VLLM_MODEL_NAME = "llm"


def create_mock_async_openai_client():
    """Create a mock AsyncOpenAI client for testing."""
    mock_client = MagicMock(spec=AsyncOpenAI)

    # Mock the chat property
    mock_chat = MagicMock()
    mock_client.chat = mock_chat

    # Mock the completions property
    mock_completions = MagicMock()

    # Create a mock ChatCompletion response
    mock_response = ChatCompletion(
        id="chatcmpl-test123",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    content="Test response",
                    role="assistant",
                ),
            )
        ],
        created=1234567890,
        model=VLLM_MODEL_NAME,
        object="chat.completion",
        usage=CompletionUsage(
            completion_tokens=10,
            prompt_tokens=5,
            total_tokens=15,
        ),
    )

    # Mock the create method as an async method that returns the mock response
    mock_completions.create = AsyncMock(return_value=mock_response)

    mock_chat.completions = mock_completions
    return mock_client, mock_chat


def test_video_input():
    mock_client, completion_mock = create_mock_async_openai_client()

    provider = OpenAIProvider(openai_client=mock_client)

    client = OpenAIChatModelVideo(
        model_name=VLLM_MODEL_NAME,
        provider=provider,
    )

    result = model_request_sync(
        model=client,
        messages=[],
    )

    # Assert the mock was called
    completion_mock.completions.create.assert_called_once()

    # Verify the result
    assert result is not None
