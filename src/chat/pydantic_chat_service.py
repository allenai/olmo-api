from pydantic import BaseModel
from pydantic_ai.direct import model_request_stream_sync, model_request_sync  # noqa: F401
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.tools import ToolDefinition

from src.config.get_config import get_config

PUBLIC_CIRRASCALE_URL = "https://aisuite.cirrascale.com/apis"


class Add(BaseModel):
    """Add two"""

    a: int
    b: int


def get_test_model(model_name: str):
    cfg = get_config()

    return OpenAIModel(
        model_name=model_name,
        provider=OpenAIProvider(base_url=cfg.modal_qwen.base_url, api_key=cfg.modal_qwen.api_key.get_secret_value()),
    )


def stream_message(user_prompt: str):
    model = get_test_model("llm")

    messages: list[ModelMessage] = [
        ModelRequest([
            # SystemPromptPart(
            #     "You are OLMo 2 Instruct, a helpful, open-source AI Assistant built by the Allen Institute for AI."
            # ),
            UserPromptPart(user_prompt),
        ])
    ]

    # response = model_request_sync(
    #     model=model,
    #     messages=messages,
    #     model_settings=OpenAIModelSettings(openai_reasoning_effort="low"),
    #     model_request_parameters=ModelRequestParameters(
    #         function_tools=[
    #             ToolDefinition(
    #                 name=Add.__name__.lower(), description=Add.__doc__, parameters_json_schema=Add.model_json_schema()
    #             )
    #         ]
    #     ),
    # )
    # yield str(response)

    with model_request_stream_sync(
        model=model,
        messages=messages,
        model_settings=OpenAIModelSettings(openai_reasoning_effort="low"),
        model_request_parameters=ModelRequestParameters(
            function_tools=[
                ToolDefinition(
                    name=Add.__name__.lower(), description=Add.__doc__, parameters_json_schema=Add.model_json_schema()
                )
            ]
        ),
    ) as stream:
        chunks = []
        for chunk in stream:
            chunks.append(chunk)
            yield str(chunk) + "\n"
