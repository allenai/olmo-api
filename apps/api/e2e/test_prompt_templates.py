from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import text

from api.prompt_template.prompt_template_service import PromptTemplateResponseList
from e2e.conftest import AuthenticatedClient, auth_headers_for_user

PROMPT_TEMPLATES_ENDPOINT = "/v5/prompt-templates/"


async def create_prompt_template_in_db(
    db_session,
    *,
    template_id: str | None = None,
    name: str = "Test Template",
    content: str = "Test content: {{variable}}",
    creator: str = "test-user",
    model_type: str = "chat",
    opts: dict | None = None,
    file_urls: list[str] | None = None,
    extra_parameters: dict | None = None,
) -> str:
    """Helper function to create a prompt template directly in the database."""
    if template_id is None:
        template_id = f"p_tpl_{uuid4().hex[:16]}"

    if opts is None:
        opts = {
            "max_tokens": 2048,
            "temperature": 0.7,
            "top_p": 1.0,
        }

    query = text("""
        INSERT INTO prompt_template (id, name, content, creator, opts, model_type, file_urls, extra_parameters)
        VALUES (:id, :name, :content, :creator, :opts, :model_type, :file_urls, :extra_parameters)
        RETURNING id
    """)

    # Convert lists and dicts to PostgreSQL-compatible format
    file_urls_array = file_urls or None

    await db_session.execute(
        query,
        {
            "id": template_id,
            "name": name,
            "content": content,
            "creator": creator,
            "opts": opts,
            "model_type": model_type,
            "file_urls": file_urls_array,
            "extra_parameters": extra_parameters,
        },
    )
    await db_session.commit()

    return template_id


async def create_tool_definition_in_db(
    db_session,
    *,
    tool_id: str | None = None,
    name: str = "test_tool",
    description: str = "A test tool",
    parameters: dict | None = None,
    tool_source: str = "USER_DEFINED",
) -> str:
    """Helper function to create a tool definition directly in the database."""
    if tool_id is None:
        tool_id = f"tool_{uuid4().hex[:16]}"

    query = text("""
        INSERT INTO tool_definition (id, name, description, parameters, tool_source)
        VALUES (:id, :name, :description, :parameters, :tool_source)
        RETURNING id
    """)

    result = await db_session.execute(
        query,
        {
            "id": tool_id,
            "name": name,
            "description": description,
            "parameters": parameters,
            "tool_source": tool_source,
        },
    )
    await db_session.commit()

    return tool_id


async def associate_tool_with_template(
    db_session,
    *,
    template_id: str,
    tool_id: str,
):
    """Helper function to associate a tool definition with a prompt template."""
    query = text("""
        INSERT INTO prompt_template_tool_definition_association (prompt_template_id, tool_definition_id)
        VALUES (:template_id, :tool_id)
    """)

    await db_session.execute(
        query,
        {
            "template_id": template_id,
            "tool_id": tool_id,
        },
    )
    await db_session.commit()

# TODO: after CRUD endpoints are added, remove these direct db update in favor of endpoints.
async def create_three_sample_templates(
    db_session,
    ) -> tuple[str, str, str]:
    """
    Helper function to create three prompt templates for testing:
    1. Basic template with minimal fields
    2. Template with a file URL
    3. Template with a tool definition

    Returns:
        Tuple of (basic_template_id, file_template_id, tool_template_id)
    """
    # 1. Create basic template
    basic_template_id = await create_prompt_template_in_db(
        db_session,
        name="Basic Template",
        content="You are a helpful assistant. Answer this question: {{question}}",
        creator="creator1",
        model_type="chat",
    )

    # 2. Create template with file URL
    file_template_id = await create_prompt_template_in_db(
        db_session,
        name="Template with File",
        content="Analyze the document at {{file_url}} and provide insights.",
        creator="creator2",
        model_type="chat",
        file_urls=["https://example.com/document.pdf"],
    )

    # 3. Create template with tool definition
    tool_template_id = await create_prompt_template_in_db(
        db_session,
        name="Template with Tool",
        content="Use the calculator tool to solve: {{math_problem}}",
        creator="creator3",
        model_type="chat",
    )

    # Create a tool definition
    tool_id = await create_tool_definition_in_db(
        db_session,
        name="calculator",
        description="Performs basic mathematical calculations",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate",
                },
            },
            "required": ["expression"],
        },
        tool_source="USER_DEFINED",
    )

    # Associate tool with the third template
    await associate_tool_with_template(
        db_session,
        template_id=tool_template_id,
        tool_id=tool_id,
    )

    return basic_template_id, file_template_id, tool_template_id


async def test_get_empty_prompt_templates_list(
    client: AsyncClient,
    auth_user: AuthenticatedClient,
):
    """Test getting an empty list of prompt templates."""
    response = await client.get(
        PROMPT_TEMPLATES_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
    )
    response.raise_for_status()

    templates = PromptTemplateResponseList.model_validate(response.json())
    assert isinstance(templates.root, list)
    assert len(templates.root) == 0


async def test_get_prompt_templates_list(
    client: AsyncClient,
    auth_user: AuthenticatedClient,
    db_session,
):
    """Test getting an empty list of prompt templates."""
    # Create prompt template list in database
    await create_three_sample_templates(db_session)

    response = await client.get(
        PROMPT_TEMPLATES_ENDPOINT,
        headers=auth_headers_for_user(auth_user),
    )
    response.raise_for_status()

    templates = PromptTemplateResponseList.model_validate(response.json())
    assert isinstance(templates.root, list)
    assert len(templates.root) == 3

    # Assert second entry has a file URL
    second_template = templates.root[1]
    assert second_template.file_urls is not None
    assert len(second_template.file_urls) > 0
    assert second_template.file_urls[0] == "https://example.com/document.pdf"

    # Assert last entry has tool definitions
    last_template = templates.root[2]
    assert len(last_template.tool_definitions) > 0
    assert last_template.tool_definitions[0].name == "calculator"
