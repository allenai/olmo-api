from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from src.config.get_config import get_config


def stream_message():
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(
            "You are OLMo 2 Instruct, a helpful, open-source AI Assistant built by the Allen Institute for AI."
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    cfg = get_config()
    model = ChatOpenAI(
        base_url=cfg.cirrascale.base_url, api_key=cfg.cirrascale.api_key, model="OLMo-2-0425-1B-Instruct"
    )

    chain = prompt | model

    response = chain.stream({"messages": [HumanMessage("Tell me about lions")]})

    for chunk in response:
        yield chunk.content
