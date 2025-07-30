from pydantic_ai.direct import model_request_stream_sync
from pydantic_ai.messages import ModelMessage, ModelRequest, SystemPromptPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.config.get_config import get_config


def get_test_model(model_name: str):
    cfg = get_config()

    return OpenAIModel(
        model_name=model_name,
        provider=OpenAIProvider(base_url=cfg.cirrascale.base_url, api_key=cfg.cirrascale.api_key.get_secret_value()),
    )


def stream_message(user_prompt: str):
    model = get_test_model("OLMo-2-0425-1B-Instruct")

    messages: list[ModelMessage] = [
        ModelRequest([
            SystemPromptPart(
                "You are OLMo 2 Instruct, a helpful, open-source AI Assistant built by the Allen Institute for AI."
            ),
            UserPromptPart(user_prompt),
        ])
    ]

    response = model_request_stream_sync(model=model, messages=messages)

    yield str(response)

    # with model_request_stream_sync(model=model, messages=messages) as stream:
    #     chunks = []
    #     for chunk in stream:
    #         chunks.append(chunk)
    #         yield chunk
