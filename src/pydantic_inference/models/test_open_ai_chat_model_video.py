from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage
from pydantic_ai import ModelRequest, UserPromptPart
from pydantic_ai.direct import model_request_sync
from pydantic_ai.messages import BinaryContent
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
    """
    This test ensure that our modified openai client continues to work with video.
    We overrode an internal method in pydatnic openai called _map_user_prompt.
    This test might break when we upgrade pydantic ai because this method could change.
    """

    mock_client, completion_mock = create_mock_async_openai_client()

    provider = OpenAIProvider(openai_client=mock_client)

    client = OpenAIChatModelVideo(
        model_name=VLLM_MODEL_NAME,
        provider=provider,
    )

    test_image_path = Path(__file__).parent.joinpath("../../../e2e/tree.mov")

    with test_image_path.open("rb") as file:
        messages = [
            ModelRequest(
                parts=[
                    UserPromptPart(
                        content=["Tell me a joke.", BinaryContent(data=file.read(), media_type="video/quicktime")],
                    ),
                ]
            ),
        ]

        result = model_request_sync(
            model=client,
            messages=messages,
        )

        # Assert the mock was called
        completion_mock.completions.create.assert_called_once()

        # Verify the result
        assert result is not None
