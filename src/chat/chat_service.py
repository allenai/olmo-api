from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from src.config.get_config import get_config


def get_test_model(model_name: str):
    cfg = get_config()

    # return ParrotFakeChatModel()

    return ChatOpenAI(base_url=cfg.cirrascale.base_url, api_key=cfg.cirrascale.api_key, model=model_name)


def stream_message(model: BaseChatModel, user_prompt: str):
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(
            "You are OLMo 2 Instruct, a helpful, open-source AI Assistant built by the Allen Institute for AI."
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt_template | model

    response = chain.stream(
        {"messages": [HumanMessage(user_prompt, id="foo")]}, config={"configurable": {"session_id": "abc"}}
    )

    full_message = ""

    for chunk in response:
        yield chunk.content
        if isinstance(chunk.content, str):
            full_message += chunk.content

    return full_message
