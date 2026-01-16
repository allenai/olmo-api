from httpx import AsyncClient

from api.prompt_template.prompt_template_service import PromptTemplateResponseList
from e2e.conftest import AuthenticatedClient, auth_headers_for_user

PROMPT_TEMPLATES_ENDPOINT = "/v5/prompt-templates/"


async def test_get_prompt_templates_list(
    client: AsyncClient,
    auth_user: AuthenticatedClient,
):
    response = await client.get(
        PROMPT_TEMPLATES_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
    )
    response.raise_for_status()

    templates = PromptTemplateResponseList.model_validate(response.json())

    # Update assertions if the fixture data changes
    assert isinstance(templates.root, list)
    assert len(templates.root) == 3

    # Assert second entry has a file URL
    second_template = templates.root[1]
    assert second_template.file_urls is not None
    assert len(second_template.file_urls) > 0
    assert (
        second_template.file_urls[0]
        == "https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/Stock_278013497.jpeg"
    )

    # Assert last entry has tool definitions
    last_template = templates.root[2]
    assert len(last_template.tool_definitions) > 0
    assert last_template.tool_definitions[0].name == "get_weather"
