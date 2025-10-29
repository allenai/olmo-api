import logging

from werkzeug import exceptions

from src.agent.agent_model import Agent
from src.api_interface import APIInterface


class AgentDTO(APIInterface):
    id: str
    name: str
    description: str
    short_summary: str
    information_url: str | None


available_agents = [
    Agent(
        id="deep-research",
        name="Tülu Deep Research",
        description="Description",
        short_summary="Summary",
        information_url=None,
        mcp_server_ids=["tulu-deep-research"],
        model_id="test-model",
        max_tokens=32_768,
        temperature=0,
        top_p=1,
        stop=[],
        n=1,
    ),
    Agent(
        id="fake-test-agent",
        name="Fake Test Agent",
        description="Fake agent for testing",
        short_summary="Fake",
        information_url=None,
        mcp_server_ids=None,
        model_id="test-model",
        max_tokens=2048,
        temperature=0,
        top_p=1,
        stop=[],
        n=1,
    ),
]


def get_agent_by_id(agent_id: str) -> Agent:
    agent = next((agent for agent in available_agents if agent.id == agent_id), None)

    if agent is None:
        logging.getLogger().error("Couldn't find agent %s", id)

        invalid_agent_message = f"Invalid agent {id}"
        raise exceptions.BadRequest(invalid_agent_message)

    return agent
