from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.language_models import BaseChatModel, ParrotFakeChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

from src.config.get_config import get_config


def get_test_model(model_name: str):
    cfg = get_config()

    return ParrotFakeChatModel()

    return ChatOpenAI(base_url=cfg.cirrascale.base_url, api_key=cfg.cirrascale.api_key, model=model_name)


def get_session_history(session_id: str):
    return InMemoryChatMessageHistory()


def stream_message(model: BaseChatModel, user_prompt: str):
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(
            "You are OLMo 2 Instruct, a helpful, open-source AI Assistant built by the Allen Institute for AI."
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    prompt = prompt_template.invoke({"messages": [HumanMessage(user_prompt)]})

    model_with_history = RunnableWithMessageHistory(model, get_session_history)

    response = model_with_history.stream(prompt, config={"configurable": {"session_id": "abc"}})

    # chain = prompt_template | model_with_history
    # response = chain.stream({"messages": [HumanMessage(user_prompt)]})

    for chunk in response:
        yield chunk.content

    # prompt_messages = prompt.to_messages()
    prompt_messages = model_with_history.messages

    return prompt_messages
